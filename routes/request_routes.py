from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
from database import get_db, get_next_sequence, serialize_doc
from config import Config
from models.helpers import (
    calculate_urgency_timeline, login_required, role_required,
    get_session_user, log_activity, BLOOD_GROUPS
)

request_bp = Blueprint('request_bp', __name__)

PRIORITY_RANKS = {'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}

@request_bp.route('/api/requests/create', methods=['POST'])
@login_required
@role_required(['HOSPITAL', 'ADMIN'])
def create_blood_request():
    """
    Hospital creates a blood request:
    - Enforces hospital identity from authenticated session for hospital users.
    - Whitelists blood groups.
    - Validates positive quantities and priority.
    """
    session_user = get_session_user()
    data = request.get_json() or {}
    blood_group = data.get('blood_group', '').strip().upper()
    quantity = data.get('quantity')
    emergency_level = data.get('emergency_level', 'MEDIUM').strip().upper()
    notes = data.get('notes', '').strip()

    if session_user.get('role') == 'HOSPITAL':
        hospital_id = session_user.get('hospital_id')
        hospital_name = session_user.get('hospital_name', session_user.get('name', 'Hospital'))
    else:
        # Admin proxy submission on behalf of hospital
        hospital_id = data.get('hospital_id') or session_user.get('hospital_id')
        hospital_name = data.get('hospital_name', 'General Hospital')

    if not hospital_id:
        return jsonify({'success': False, 'message': 'Hospital account authentication required'}), 401

    if not blood_group or blood_group not in BLOOD_GROUPS:
        return jsonify({'success': False, 'message': f'Invalid blood group. Allowed: {", ".join(BLOOD_GROUPS)}'}), 400

    try:
        quantity = int(quantity)
        if quantity <= 0 or quantity > 100:
            return jsonify({'success': False, 'message': 'Requested quantity must be between 1 and 100 units'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Quantity must be a valid integer'}), 400

    if emergency_level not in ['HIGH', 'MEDIUM', 'LOW']:
        emergency_level = 'MEDIUM'

    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    hospital = db.hospitals.find_one({'hospital_id': hospital_id})
    if hospital:
        hospital_name = hospital.get('name', hospital_name)

    now = datetime.now()
    urgency_info = calculate_urgency_timeline(emergency_level, created_at=now, request_status='Pending')
    req_id = get_next_sequence('blood_req_seq', prefix='REQ', start_val=1001)

    request_doc = {
        'request_id': req_id,
        'hospital_id': hospital_id,
        'hospital_name': hospital_name,
        'blood_group': blood_group,
        'quantity': quantity,
        'approved_quantity': 0,
        'remaining_quantity': quantity,
        'emergency_level': emergency_level,
        'priority_rank': PRIORITY_RANKS.get(emergency_level, 2),
        'emergency_hours': urgency_info['duration_hours'],
        'required_by_time': urgency_info['required_by'],
        'status': 'Pending',  # Allowed: Pending | Partially Approved | Approved | Rejected | Cancelled
        'issued_bag_ids': [],
        'fulfilments': [],
        'invoice_ids': [],
        'notes': notes,
        'admin_remarks': None,
        'created_at': now,
        'updated_at': now
    }

    db.blood_requests.insert_one(request_doc)
    log_activity(db, hospital_id, hospital_name, session_user.get('role'), 'CREATE_REQUEST', f'Submitted blood request {req_id} for {quantity} unit(s) of {blood_group} [{emergency_level}]', target_type='REQUEST', target_id=req_id)

    return jsonify({
        'success': True,
        'message': f'Blood request {req_id} submitted with {emergency_level} urgency ({urgency_info["duration_hours"]}h window).',
        'request': serialize_doc(request_doc)
    }), 201


@request_bp.route('/api/requests', methods=['GET'])
@login_required
def list_blood_requests():
    """
    List blood requests:
    - Super Admin sees all requests sorted by priority ranking, deadline, then created time.
    - Hospital sees exclusively their own requests from their authenticated session.
    """
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    session_user = get_session_user()
    status = request.args.get('status')
    emergency = request.args.get('emergency')
    blood_group = request.args.get('blood_group')

    query = {}
    if session_user.get('role') == 'HOSPITAL':
        query['hospital_id'] = session_user.get('hospital_id')
    else:
        hospital_id = request.args.get('hospital_id')
        if hospital_id:
            query['hospital_id'] = hospital_id

    if status and status != 'ALL':
        query['status'] = status
    if emergency and emergency != 'ALL':
        query['emergency_level'] = emergency
    if blood_group and blood_group != 'ALL':
        query['blood_group'] = blood_group

    requests_list = list(db.blood_requests.find(query).sort([
        ('status', 1),
        ('priority_rank', 1),
        ('required_by_time', 1),
        ('created_at', -1)
    ]))

    now = datetime.now()
    # Calculate live time remaining for active requests
    for r in requests_list:
        req_by_str = r.get('required_by_time')
        req_status = r.get('status', 'Pending')
        urgency = calculate_urgency_timeline(r.get('emergency_level'), created_at=r.get('created_at'), request_status=req_status)
        r['is_overdue'] = urgency['is_overdue']
        r['seconds_remaining'] = urgency['seconds_remaining']
        
        if not urgency['is_awaiting_fulfilment']:
            r['time_remaining_formatted'] = f"Completed ({req_status})"
        elif r['is_overdue']:
            r['time_remaining_formatted'] = "OVERDUE"
        else:
            diff_sec = urgency['seconds_remaining']
            r['time_remaining_formatted'] = f"{diff_sec // 3600}h {(diff_sec % 3600) // 60}m"

    return jsonify({
        'success': True,
        'count': len(requests_list),
        'requests': serialize_doc(requests_list)
    })


@request_bp.route('/api/requests/<request_id>/process', methods=['POST'])
@login_required
@role_required(['ADMIN'])
def process_blood_request(request_id):
    """
    Super Admin Request Processing (FEFO - First Expiry, First Out):
    - Concurrency protection: reserves each bag conditionally requiring status == 'Available'.
    - Partial approval logic: records a separate fulfilment entry and generates an invoice for the issued batch.
    - Idempotency check: prevents re-processing completed or cancelled requests.
    """
    data = request.get_json() or {}
    decision = data.get('decision', '').strip().upper()  # APPROVE_FULL | PARTIAL_APPROVE | REJECT
    approved_qty = data.get('approved_qty')
    remarks = data.get('remarks', '').strip()
    session_user = get_session_user()

    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    req_doc = db.blood_requests.find_one({'request_id': request_id})
    if not req_doc:
        return jsonify({'success': False, 'message': f'Request {request_id} not found'}), 404

    current_status = req_doc.get('status')
    if current_status in ['Approved', 'Rejected', 'Cancelled']:
        return jsonify({'success': False, 'message': f'Request {request_id} is already finalized ({current_status})'}), 400

    now = datetime.now()
    blood_group = req_doc.get('blood_group')
    hospital_id = req_doc.get('hospital_id')
    hospital_name = req_doc.get('hospital_name')
    requested_quantity = req_doc.get('quantity', 0)
    already_approved = req_doc.get('approved_quantity', 0)
    remaining_to_issue = req_doc.get('remaining_quantity', requested_quantity - already_approved)

    # 1. Decision: REJECT
    if decision == 'REJECT':
        # If some units were already issued in a previous partial batch, preserve those and mark remainder as Rejected/Closed
        new_status = 'Approved' if already_approved == requested_quantity else ('Partially Approved' if already_approved > 0 else 'Rejected')
        if already_approved > 0:
            db.blood_requests.update_one(
                {'request_id': request_id},
                {
                    '$set': {
                        'remaining_quantity': 0,
                        'status': 'Approved',  # Closed with partial issue
                        'admin_remarks': remarks or f'Remaining {remaining_to_issue} units closed/rejected by Super Admin. Previously issued {already_approved} units preserved.',
                        'updated_at': now
                    }
                }
            )
            msg = f'Request {request_id} remaining {remaining_to_issue} units rejected. Previously issued {already_approved} units remain active with valid invoices.'
        else:
            db.blood_requests.update_one(
                {'request_id': request_id},
                {
                    '$set': {
                        'status': 'Rejected',
                        'admin_remarks': remarks or 'Request rejected by Super Admin.',
                        'updated_at': now
                    }
                }
            )
            msg = f'Request {request_id} has been REJECTED.'

        log_activity(db, session_user.get('user_id', 'ADMIN'), session_user.get('name', 'Admin'), 'ADMIN', 'REJECT_REQUEST', msg, target_type='REQUEST', target_id=request_id)
        return jsonify({'success': True, 'message': msg, 'status': 'Rejected'})

    # Query available, screened, unexpired bags sorted by FEFO (Earliest Expiry First)
    available_candidate_bags = list(db.blood_bags.find({
        'blood_group': blood_group,
        'status': 'Available',
        'expiry_date': {'$gte': now}
    }).sort('expiry_date', 1))

    available_stock_count = len(available_candidate_bags)

    if decision == 'APPROVE_FULL':
        units_to_issue = remaining_to_issue
        if available_stock_count < units_to_issue:
            return jsonify({
                'success': False,
                'message': f'Insufficient stock! Required: {units_to_issue} units of {blood_group}, but only {available_stock_count} units available. Consider Partial Approval.',
                'available_stock': available_stock_count,
                'required': units_to_issue
            }), 400
    elif decision == 'PARTIAL_APPROVE':
        try:
            units_to_issue = int(approved_qty) if approved_qty is not None else min(available_stock_count, remaining_to_issue)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid approved quantity specified'}), 400

        if units_to_issue <= 0:
            return jsonify({'success': False, 'message': 'Approved quantity must be at least 1'}), 400
        if units_to_issue > remaining_to_issue:
            return jsonify({'success': False, 'message': f'Cannot approve more than remaining needed quantity ({remaining_to_issue})'}), 400
        if units_to_issue > available_stock_count:
            return jsonify({'success': False, 'message': f'Only {available_stock_count} units available in stock right now'}), 400
    else:
        return jsonify({'success': False, 'message': f'Invalid decision: {decision}. Use APPROVE_FULL, PARTIAL_APPROVE, or REJECT'}), 400

    # Atomic FEFO Allocation: conditionally claim each bag
    allocated_bags = []
    for candidate in available_candidate_bags:
        if len(allocated_bags) >= units_to_issue:
            break
        # Conditional update ensuring bag is still Available
        claimed = db.blood_bags.find_one_and_update(
            {
                'bag_id': candidate['bag_id'],
                'status': 'Available',
                'expiry_date': {'$gte': now}
            },
            {
                '$set': {
                    'status': 'Issued',
                    'issued_to_hospital_id': hospital_id,
                    'issued_to_hospital_name': hospital_name,
                    'issued_date': now,
                    'request_id': request_id
                }
            },
            return_document=True
        )
        if claimed:
            allocated_bags.append(claimed)

    if len(allocated_bags) < units_to_issue:
        # Race condition rollback if some bags were claimed concurrently
        for b in allocated_bags:
            db.blood_bags.update_one({'bag_id': b['bag_id']}, {'$set': {'status': 'Available', 'request_id': None, 'issued_to_hospital_id': None}})
        return jsonify({'success': False, 'message': 'Stock was concurrently allocated to another request. Please refresh and retry.'}), 409

    allocated_bag_ids = [b['bag_id'] for b in allocated_bags]
    new_approved_total = already_approved + len(allocated_bag_ids)
    new_remaining = requested_quantity - new_approved_total
    all_issued_bag_ids = req_doc.get('issued_bag_ids', []) + allocated_bag_ids

    # Step: Generate Invoice for this specific issued batch
    unit_price = Config.BLOOD_PRICES.get(blood_group, 2500)
    subtotal = sum(b.get('selling_price', unit_price) for b in allocated_bags)
    tax_amount = round(subtotal * Config.TAX_RATE, 2)
    total_amount = round(subtotal + tax_amount, 2)

    invoice_number = get_next_sequence('invoice_seq', prefix='INV', start_val=1001)

    invoice_doc = {
        'invoice_number': invoice_number,
        'request_id': request_id,
        'hospital_id': hospital_id,
        'hospital_name': hospital_name,
        'blood_group': blood_group,
        'quantity': len(allocated_bag_ids),
        'blood_bags': allocated_bag_ids,
        'unit_price': unit_price,
        'subtotal': subtotal,
        'tax_rate_percent': int(Config.TAX_RATE * 100),
        'tax_amount': tax_amount,
        'total_amount': total_amount,
        'status': 'PENDING',  # PENDING | PAID
        'invoice_date': now,
        'paid_date': None,
        'payment_reference': None,
        'created_at': now
    }
    db.invoices.insert_one(invoice_doc)

    # Atomically update Hospital outstanding balance for this issued batch
    db.hospitals.update_one(
        {'hospital_id': hospital_id},
        {
            '$inc': {'outstanding_balance': total_amount},
            '$set': {'updated_at': now}
        }
    )

    # Record fulfilment record
    fulfilment_entry = {
        'fulfilment_id': f"FUL-{invoice_number}",
        'issued_count': len(allocated_bag_ids),
        'bag_ids': allocated_bag_ids,
        'invoice_number': invoice_number,
        'total_amount': total_amount,
        'issued_at': now.isoformat(),
        'issued_by': session_user.get('name', 'Super Admin')
    }

    is_fully_approved = (new_remaining == 0)
    final_status = 'Approved' if is_fully_approved else 'Partially Approved'

    existing_invoices = req_doc.get('invoice_ids', [])
    existing_invoices.append(invoice_number)

    db.blood_requests.update_one(
        {'request_id': request_id},
        {
            '$set': {
                'approved_quantity': new_approved_total,
                'remaining_quantity': new_remaining,
                'status': final_status,
                'issued_bag_ids': all_issued_bag_ids,
                'admin_remarks': remarks or f'Issued {len(allocated_bag_ids)} unit(s) via FEFO. Invoice {invoice_number} generated.',
                'invoice_id': invoice_number,  # Latest invoice
                'updated_at': now
            },
            '$push': {
                'fulfilments': fulfilment_entry,
                'invoice_ids': invoice_number
            }
        }
    )

    msg = f'Issued {len(allocated_bag_ids)} bag(s) [{", ".join(allocated_bag_ids)}] via FEFO. Invoice {invoice_number} generated (₹{total_amount:.2f}).'
    if is_fully_approved:
        msg += f' Request {request_id} is now fully APPROVED.'
    else:
        msg += f' Request {request_id} is PARTIALLY APPROVED. {new_remaining} unit(s) remaining.'

    log_activity(db, session_user.get('user_id', 'ADMIN'), session_user.get('name', 'Admin'), 'ADMIN', 'DISPATCH_BLOOD', msg, target_type='REQUEST', target_id=request_id)

    return jsonify({
        'success': True,
        'message': msg,
        'status': final_status,
        'issued_bags': allocated_bag_ids,
        'approved_quantity': new_approved_total,
        'remaining_quantity': new_remaining,
        'invoice': serialize_doc(invoice_doc)
    })


@request_bp.route('/api/requests/<request_id>/cancel', methods=['POST'])
@login_required
def cancel_blood_request(request_id):
    """
    Cancel an unfulfilled request or cancel the remaining portion of a partially approved request.
    Already issued bags and their invoices are preserved.
    """
    session_user = get_session_user()
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    query = {'request_id': request_id}
    if session_user.get('role') == 'HOSPITAL':
        query['hospital_id'] = session_user.get('hospital_id')

    req_doc = db.blood_requests.find_one(query)
    if not req_doc:
        return jsonify({'success': False, 'message': 'Request not found or access unauthorized'}), 404

    current_status = req_doc.get('status')
    if current_status in ['Approved', 'Rejected', 'Cancelled']:
        return jsonify({'success': False, 'message': f'Cannot cancel request with status: {current_status}'}), 400

    already_issued = req_doc.get('approved_quantity', 0)
    now = datetime.now()

    if already_issued > 0:
        # Partially issued: close the remainder while keeping the issued units
        db.blood_requests.update_one(
            {'request_id': request_id},
            {
                '$set': {
                    'remaining_quantity': 0,
                    'status': 'Approved',  # Closed with partial issue
                    'admin_remarks': f'Remaining units cancelled by {session_user.get("name")}. {already_issued} issued units remain billed.',
                    'updated_at': now
                }
            }
        )
        msg = f'Remaining unfulfilled units cancelled. Issued {already_issued} bags remain active.'
    else:
        db.blood_requests.update_one(
            {'request_id': request_id},
            {
                '$set': {
                    'status': 'Cancelled',
                    'admin_remarks': f'Cancelled by {session_user.get("name")}.',
                    'updated_at': now
                }
            }
        )
        msg = f'Request {request_id} has been cancelled successfully.'

    log_activity(db, session_user.get('user_id') or session_user.get('hospital_id'), session_user.get('name'), session_user.get('role'), 'CANCEL_REQUEST', msg, target_type='REQUEST', target_id=request_id)

    return jsonify({
        'success': True,
        'message': msg
    })
