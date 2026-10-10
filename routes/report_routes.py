import io
import csv
from datetime import datetime
from flask import Blueprint, request, jsonify, Response, session
from database import get_db, serialize_doc
from config import Config
from models.helpers import login_required, role_required, BLOOD_GROUPS

report_bp = Blueprint('report_bp', __name__)

@report_bp.route('/api/reports/dashboard-stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    """
    Unified Dashboard Metrics:
    - Available blood bags (screened & unexpired)
    - Active requests (awaiting fulfilment)
    - Expiring soon count (<= 7 days)
    - Outstanding balance
    - Donors, Invoices, and Revenue
    """
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    now = datetime.now()

    total_donors = db.donors.count_documents({})
    eligible_donors = db.donors.count_documents({'eligible': True})
    
    total_bags = db.blood_bags.count_documents({})
    available_bags = db.blood_bags.count_documents({'status': 'Available', 'expiry_date': {'$gte': now}})
    pending_screening = db.blood_bags.count_documents({'status': 'Pending Screening'})
    issued_bags = db.blood_bags.count_documents({'status': 'Issued'})
    expired_bags = db.blood_bags.count_documents({
        '$or': [
            {'status': 'Expired'},
            {'status': 'Available', 'expiry_date': {'$lt': now}}
        ]
    })

    # Expiring soon (within 7 days)
    expiring_soon_count = 0
    available_bag_docs = list(db.blood_bags.find({'status': 'Available', 'expiry_date': {'$gte': now}}))
    for b in available_bag_docs:
        exp_dt = b.get('expiry_date')
        if isinstance(exp_dt, str):
            try:
                exp_dt = datetime.fromisoformat(exp_dt.replace("Z", ""))
            except Exception:
                exp_dt = None
        if exp_dt and (exp_dt - now).days <= 7:
            expiring_soon_count += 1

    total_hospitals = db.hospitals.count_documents({})
    total_coordinators = db.coordinators.count_documents({})

    total_requests = db.blood_requests.count_documents({})
    pending_requests = db.blood_requests.count_documents({'status': 'Pending'})
    partial_requests = db.blood_requests.count_documents({'status': 'Partially Approved'})
    active_requests = pending_requests + partial_requests
    approved_requests = db.blood_requests.count_documents({'status': 'Approved'})
    rejected_requests = db.blood_requests.count_documents({'status': 'Rejected'})
    cancelled_requests = db.blood_requests.count_documents({'status': 'Cancelled'})

    all_invoices = list(db.invoices.find({}))
    total_revenue_billed = sum(i.get('total_amount', 0) for i in all_invoices)
    total_revenue_collected = sum(i.get('total_amount', 0) for i in all_invoices if i.get('status') == 'PAID')
    total_outstanding = total_revenue_billed - total_revenue_collected

    return jsonify({
        'success': True,
        'stats': {
            'donors': {
                'total': total_donors,
                'eligible': eligible_donors,
                'ineligible': total_donors - eligible_donors
            },
            'inventory': {
                'total_collected': total_bags,
                'available': available_bags,
                'pending_screening': pending_screening,
                'expiring_soon': expiring_soon_count,
                'issued': issued_bags,
                'expired': expired_bags
            },
            'requests': {
                'total': total_requests,
                'active': active_requests,
                'pending': pending_requests,
                'partial': partial_requests,
                'approved': approved_requests,
                'rejected': rejected_requests,
                'cancelled': cancelled_requests
            },
            'finance': {
                'billed': round(total_revenue_billed, 2),
                'collected': round(total_revenue_collected, 2),
                'outstanding': round(total_outstanding, 2),
                'invoices_count': len(all_invoices),
                'paid_count': sum(1 for i in all_invoices if i.get('status') == 'PAID'),
                'pending_count': sum(1 for i in all_invoices if i.get('status') == 'PENDING')
            },
            'entities': {
                'hospitals': total_hospitals,
                'coordinators': total_coordinators
            }
        }
    })


@report_bp.route('/api/reports/alerts', methods=['GET'])
@login_required
def get_inventory_alerts():
    """
    Separate real-time alerts for:
    1. Low Quantity Alerts (blood group stock < 3 units)
    2. Approaching Expiry Alerts (bags expiring within 7 days)
    3. Urgent Pending Requests Alerts
    """
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    now = datetime.now()

    # 1. Low Quantity
    low_stock_alerts = []
    for bg in BLOOD_GROUPS:
        cnt = db.blood_bags.count_documents({'blood_group': bg, 'status': 'Available', 'expiry_date': {'$gte': now}})
        if cnt == 0:
            low_stock_alerts.append({
                'blood_group': bg,
                'level': 'OUT_OF_STOCK',
                'count': 0,
                'message': f'Blood Group {bg} is completely OUT OF STOCK (0 units available).'
            })
        elif cnt < 3:
            low_stock_alerts.append({
                'blood_group': bg,
                'level': 'LOW_STOCK',
                'count': cnt,
                'message': f'Blood Group {bg} is LOW IN STOCK ({cnt} unit(s) remaining).'
            })

    # 2. Approaching Expiry
    expiring_soon_alerts = []
    available_bags = list(db.blood_bags.find({'status': 'Available', 'expiry_date': {'$gte': now}}))
    for b in available_bags:
        exp_dt = b.get('expiry_date')
        if isinstance(exp_dt, str):
            try:
                exp_dt = datetime.fromisoformat(exp_dt.replace("Z", ""))
            except Exception:
                exp_dt = None
        if exp_dt:
            days_left = (exp_dt - now).days
            if days_left <= 7:
                expiring_soon_alerts.append({
                    'bag_id': b.get('bag_id'),
                    'blood_group': b.get('blood_group'),
                    'days_remaining': days_left,
                    'expiry_date': str(exp_dt)[:10],
                    'storage_location': b.get('storage_location'),
                    'message': f'Bag {b.get("bag_id")} ({b.get("blood_group")}) expires in {days_left} day(s).'
                })

    # 3. Urgent Requests
    urgent_requests = list(db.blood_requests.find({
        'status': {'$in': ['Pending', 'Partially Approved']},
        'emergency_level': 'HIGH'
    }))

    return jsonify({
        'success': True,
        'low_stock_alerts': low_stock_alerts,
        'expiring_soon_alerts': expiring_soon_alerts,
        'urgent_requests_count': len(urgent_requests)
    })


@report_bp.route('/api/reports/activity-log', methods=['GET'])
@login_required
@role_required(['ADMIN', 'COORDINATOR'])
def get_activity_log():
    """
    Audit log of all system approvals, donations, screenings, dispatches, and payments.
    """
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    limit = min(int(request.args.get('limit', 50)), 200)
    actor_id = request.args.get('actor_id')
    action = request.args.get('action')

    query = {}
    if actor_id:
        query['actor_id'] = actor_id
    if action:
        query['action'] = action

    logs = list(db.activity_logs.find(query).sort('timestamp', -1).limit(limit))

    return jsonify({
        'success': True,
        'count': len(logs),
        'logs': serialize_doc(logs)
    })


@report_bp.route('/api/reports/export/text', methods=['GET'])
@login_required
@role_required(['ADMIN'])
def export_text_audit_report():
    """
    Generates a full comprehensive text document audit report.
    """
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not reachable'}), 503

    now = datetime.now()
    output = []
    output.append("================================================================================")
    output.append("                 BLOOD BANK MANAGEMENT SYSTEM - AUDIT REPORT                     ")
    output.append(f" Generated At : {now.strftime('%d-%b-%Y %H:%M:%S UTC')}                          ")
    output.append("================================================================================\n")

    # Inventory Section
    output.append("1. LIVE USABLE BLOOD STOCK (FEFO EVALUATION)")
    output.append("--------------------------------------------------------------------------------")
    output.append(f"{'Blood Group':<15} {'Usable Bags':<15} {'Good (>7d)':<15} {'Critical (<=7d)':<15} {'Price (INR)':<15}")
    output.append("-" * 75)

    for bg in BLOOD_GROUPS:
        bags = list(db.blood_bags.find({'blood_group': bg, 'status': 'Available', 'expiry_date': {'$gte': now}}))
        cnt = len(bags)
        good = sum(1 for b in bags if isinstance(b.get('expiry_date'), datetime) and (b.get('expiry_date') - now).days > 7)
        crit = cnt - good
        price = Config.BLOOD_PRICES.get(bg, 2500)
        output.append(f"{bg:<15} {cnt:<15} {good:<15} {crit:<15} Rs.{price:<15}")

    # Finance Section
    output.append("\n2. BILLING & REVENUE LEDGER")
    output.append("--------------------------------------------------------------------------------")
    invoices = list(db.invoices.find({}))
    total_billed = sum(i.get('total_amount', 0) for i in invoices)
    total_collected = sum(i.get('total_amount', 0) for i in invoices if i.get('status') == 'PAID')
    outstanding = total_billed - total_collected

    output.append(f" Total Invoices Generated : {len(invoices)}")
    output.append(f" Total Revenue Billed     : Rs. {total_billed:,.2f}")
    output.append(f" Total Revenue Collected  : Rs. {total_collected:,.2f}")
    output.append(f" Total Outstanding Due    : Rs. {outstanding:,.2f}\n")

    content = "\n".join(output)
    return Response(
        content,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename=BloodBank_Audit_Report_{now.strftime('%Y%m%d')}.txt"}
    )


@report_bp.route('/api/reports/export/csv/<entity>', methods=['GET'])
@login_required
@role_required(['ADMIN'])
def export_csv_data(entity):
    """
    Export sanitized database collections to CSV.
    """
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not reachable'}), 503

    now = datetime.now()
    string_io = io.StringIO()
    writer = None

    if entity == 'bloodbags':
        bags = list(db.blood_bags.find({}))
        writer = csv.writer(string_io)
        writer.writerow(['Bag ID', 'Blood Group', 'Donor ID', 'Donor Name', 'Collection Date', 'Expiry Date', 'Volume (ml)', 'Status', 'Screening', 'Storage Location', 'Price (INR)', 'Hospital'])
        for b in bags:
            writer.writerow([
                b.get('bag_id'), b.get('blood_group'), b.get('donor_id'), b.get('donor_name'),
                str(b.get('collection_date'))[:10], str(b.get('expiry_date'))[:10],
                b.get('volume_ml'), b.get('status'), b.get('screening_status', 'N/A'),
                b.get('storage_location'), b.get('selling_price'), b.get('issued_to_hospital_name', 'N/A')
            ])
    elif entity == 'requests':
        reqs = list(db.blood_requests.find({}))
        writer = csv.writer(string_io)
        writer.writerow(['Request ID', 'Hospital ID', 'Hospital Name', 'Blood Group', 'Requested Qty', 'Approved Qty', 'Remaining Qty', 'Emergency Level', 'Status', 'Created At'])
        for r in reqs:
            writer.writerow([
                r.get('request_id'), r.get('hospital_id'), r.get('hospital_name'),
                r.get('blood_group'), r.get('quantity'), r.get('approved_quantity', 0),
                r.get('remaining_quantity', r.get('quantity')), r.get('emergency_level'),
                r.get('status'), str(r.get('created_at'))[:19]
            ])
    elif entity == 'invoices':
        invs = list(db.invoices.find({}))
        writer = csv.writer(string_io)
        writer.writerow(['Invoice No', 'Request ID', 'Hospital ID', 'Hospital Name', 'Blood Group', 'Qty', 'Subtotal', 'Tax Amount', 'Total Amount', 'Status', 'Payment Ref', 'Invoice Date'])
        for i in invs:
            writer.writerow([
                i.get('invoice_number'), i.get('request_id'), i.get('hospital_id'),
                i.get('hospital_name'), i.get('blood_group'), i.get('quantity'),
                i.get('subtotal'), i.get('tax_amount'), i.get('total_amount'),
                i.get('status'), i.get('payment_reference', 'N/A'), str(i.get('invoice_date'))[:10]
            ])
    elif entity == 'donors':
        donors = list(db.donors.find({}))
        writer = csv.writer(string_io)
        writer.writerow(['Donor ID', 'Name', 'Age', 'Gender', 'Blood Group', 'Weight (kg)', 'Contact', 'Email', 'Total Donations', 'Eligible', 'Next Eligible Date', 'Status'])
        for d in donors:
            writer.writerow([
                d.get('donor_id'), d.get('name'), d.get('age'), d.get('gender'),
                d.get('blood_group'), d.get('weight'), d.get('contact'), d.get('email'),
                d.get('total_donations', 0), d.get('eligible'), d.get('next_eligible_date', 'N/A'),
                d.get('status', 'Active')
            ])
    elif entity == 'hospitals':
        hosps = list(db.hospitals.find({}))
        writer = csv.writer(string_io)
        writer.writerow(['Hospital ID', 'Hospital Name', 'Email', 'Phone', 'Address', 'Outstanding Balance (INR)', 'Status'])
        for h in hosps:
            writer.writerow([
                h.get('hospital_id'), h.get('name'), h.get('email'), h.get('phone'),
                h.get('address'), h.get('outstanding_balance', 0.0), h.get('status', 'ACTIVE')
            ])
    else:
        return jsonify({'success': False, 'message': f'Unknown export target: {entity}'}), 400

    string_io.seek(0)
    return Response(
        string_io.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=BloodBank_{entity}_{now.strftime('%Y%m%d')}.csv"}
    )
