from flask import Blueprint, request, jsonify, session
from datetime import datetime
from database import get_db, serialize_doc, get_next_sequence
from models.helpers import login_required, get_session_user, log_activity

invoice_bp = Blueprint('invoice_bp', __name__)

@invoice_bp.route('/api/invoices', methods=['GET'])
@login_required
def list_invoices():
    """
    List invoices:
    - Super Admin sees all invoices across the system.
    - Hospital sees exclusively their own invoices based on authenticated session.
    """
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    session_user = get_session_user()
    status = request.args.get('status')
    query = {}

    if session_user.get('role') == 'HOSPITAL':
        query['hospital_id'] = session_user.get('hospital_id')
    else:
        hospital_id = request.args.get('hospital_id')
        if hospital_id:
            query['hospital_id'] = hospital_id

    if status and status != 'ALL':
        query['status'] = status.upper()

    invoices = list(db.invoices.find(query).sort('invoice_date', -1))

    # Calculate summary stats
    total_amount = sum(inv.get('total_amount', 0) for inv in invoices)
    paid_amount = sum(inv.get('total_amount', 0) for inv in invoices if inv.get('status') == 'PAID')
    pending_amount = sum(inv.get('total_amount', 0) for inv in invoices if inv.get('status') == 'PENDING')

    return jsonify({
        'success': True,
        'count': len(invoices),
        'total_amount': round(total_amount, 2),
        'paid_amount': round(paid_amount, 2),
        'pending_amount': round(pending_amount, 2),
        'invoices': serialize_doc(invoices)
    })


@invoice_bp.route('/api/invoices/<invoice_number>', methods=['GET'])
@login_required
def get_invoice_detail(invoice_number):
    """
    Get detailed breakdown of an invoice:
    - Enforces ownership: Hospital can only inspect their own invoices.
    """
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    session_user = get_session_user()
    invoice = db.invoices.find_one({'invoice_number': invoice_number})
    if not invoice:
        return jsonify({'success': False, 'message': f'Invoice {invoice_number} not found'}), 404

    # Permission check
    if session_user.get('role') == 'HOSPITAL' and invoice.get('hospital_id') != session_user.get('hospital_id'):
        return jsonify({'success': False, 'message': 'Access forbidden: You can only view your own hospital invoices'}), 403

    # Fetch hospital details
    hospital = db.hospitals.find_one({'hospital_id': invoice.get('hospital_id')})

    # Fetch details of issued blood bags
    bag_ids = invoice.get('blood_bags', [])
    bags = list(db.blood_bags.find({'bag_id': {'$in': bag_ids}}))

    return jsonify({
        'success': True,
        'invoice': serialize_doc(invoice),
        'hospital': serialize_doc(hospital),
        'bags': serialize_doc(bags)
    })


@invoice_bp.route('/api/invoices/<invoice_number>/pay', methods=['POST'])
@login_required
def pay_invoice(invoice_number):
    """
    Hospital Pays Invoice (Demo / Online Payment Gateway Flow):
    - Enforces ownership: only the billed hospital (or Super Admin) can pay the invoice.
    - Idempotent and race-condition protected: updates status from PENDING to PAID atomically.
    - Requires exact positive payment amount.
    - Records an immutable payment transaction in the 'payments' collection.
    - Atomically reduces hospital outstanding balance.
    """
    session_user = get_session_user()
    data = request.get_json() or {}
    payment_amount = data.get('payment_amount')
    payment_method = data.get('payment_method', 'Online Banking / Demo Gateway')
    
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    invoice = db.invoices.find_one({'invoice_number': invoice_number})
    if not invoice:
        return jsonify({'success': False, 'message': f'Invoice {invoice_number} not found'}), 404

    # Ownership enforcement
    if session_user.get('role') == 'HOSPITAL' and invoice.get('hospital_id') != session_user.get('hospital_id'):
        return jsonify({'success': False, 'message': 'Access forbidden: You cannot pay another hospital invoice'}), 403

    if invoice.get('status') == 'PAID':
        return jsonify({'success': False, 'message': f'Invoice {invoice_number} has already been PAID'}), 400

    total_due = round(float(invoice.get('total_amount', 0)), 2)

    try:
        payment_amount = round(float(payment_amount), 2) if payment_amount is not None else total_due
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid payment amount specified'}), 400

    if payment_amount <= 0:
        return jsonify({'success': False, 'message': 'Payment amount must be greater than zero'}), 400

    # Verification: Require exact invoice amount for this transaction
    if abs(payment_amount - total_due) > 0.01:
        return jsonify({
            'success': False,
            'message': f'Exact payment required! Total payable is ₹{total_due:.2f}, but entered ₹{payment_amount:.2f}.',
            'total_due': total_due,
            'entered_amount': payment_amount
        }), 400

    now = datetime.now()
    hospital_id = invoice.get('hospital_id')
    payment_id = get_next_sequence('payment_seq', prefix='PAY', start_val=1001)
    transaction_ref = data.get('transaction_ref') or f'TXN-DEMO-{now.strftime("%Y%m%d%H%M%S")}'

    # Atomic invoice update from PENDING to PAID (prevents double payments under concurrent requests)
    paid_invoice = db.invoices.find_one_and_update(
        {
            'invoice_number': invoice_number,
            'status': 'PENDING'
        },
        {
            '$set': {
                'status': 'PAID',
                'paid_date': now,
                'paid_amount': total_due,
                'payment_id': payment_id,
                'payment_method': payment_method,
                'payment_reference': transaction_ref,
                'is_demo_payment': True,
                'updated_at': now
            }
        },
        return_document=True
    )

    if not paid_invoice:
        return jsonify({'success': False, 'message': 'Payment failed: Invoice is already paid or being processed.'}), 409

    # Record immutable payment record
    payment_doc = {
        'payment_id': payment_id,
        'invoice_number': invoice_number,
        'hospital_id': hospital_id,
        'amount': total_due,
        'payment_method': payment_method,
        'transaction_reference': transaction_ref,
        'payer_name': session_user.get('name', 'Hospital Authority'),
        'paid_at': now,
        'status': 'SUCCESS'
    }
    db.payments.insert_one(payment_doc)

    # Decrease Hospital Outstanding Balance atomically
    hospital = db.hospitals.find_one_and_update(
        {'hospital_id': hospital_id},
        {
            '$inc': {'outstanding_balance': -total_due},
            '$set': {'updated_at': now}
        },
        return_document=True
    )

    new_balance = hospital.get('outstanding_balance', 0) if hospital else 0
    if abs(new_balance) < 0.001:
        new_balance = 0.0
        db.hospitals.update_one({'hospital_id': hospital_id}, {'$set': {'outstanding_balance': 0.0}})

    msg = f'Payment of ₹{total_due:.2f} completed successfully! Invoice {invoice_number} is now marked as PAID [Ref: {transaction_ref}].'
    log_activity(db, hospital_id, session_user.get('name'), session_user.get('role'), 'INVOICE_PAYMENT', msg, target_type='INVOICE', target_id=invoice_number)

    return jsonify({
        'success': True,
        'message': msg,
        'invoice_number': invoice_number,
        'payment_id': payment_id,
        'paid_amount': total_due,
        'transaction_ref': transaction_ref,
        'new_outstanding_balance': round(new_balance, 2)
    })
