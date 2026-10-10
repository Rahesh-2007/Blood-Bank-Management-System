from flask import Blueprint, request, jsonify
from datetime import datetime
from database import get_db, serialize_doc
from config import Config
from models.helpers import login_required, BLOOD_GROUPS

stock_bp = Blueprint('stock_bp', __name__)

@stock_bp.route('/api/stock/summary', methods=['GET'])
@login_required
def get_stock_summary():
    """
    Returns usable available stock per blood group:
    Only bags satisfying: Status == 'Available' AND Expiry Date >= Current Date.
    Categorizes stock into: Good (>7 days to expiry), Critical (<=7 days to expiry), Low Stock (<3 bags), Out of Stock (0).
    """
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    now = datetime.now()

    # Query all available unexpired screened bags
    available_bags = list(db.blood_bags.find({
        'status': 'Available',
        'expiry_date': {'$gte': now}
    }))

    # Group available unexpired bags by blood group
    groups_data = {bg: {'total': 0, 'good': 0, 'critical': 0} for bg in BLOOD_GROUPS}

    for bag in available_bags:
        bg = bag.get('blood_group')
        if bg in groups_data:
            groups_data[bg]['total'] += 1
            exp_date = bag.get('expiry_date')
            if isinstance(exp_date, str):
                try:
                    exp_date = datetime.fromisoformat(exp_date.replace("Z", ""))
                except Exception:
                    exp_date = None
            if exp_date:
                days_left = (exp_date - now).days
                if days_left <= 7:
                    groups_data[bg]['critical'] += 1
                else:
                    groups_data[bg]['good'] += 1
            else:
                groups_data[bg]['good'] += 1

    summary = []
    total_usable_bags = 0
    total_expiring_soon = 0
    total_low_stock_groups = 0

    for bg in BLOOD_GROUPS:
        data = groups_data[bg]
        cnt = data['total']
        good_cnt = data['good']
        crit_cnt = data['critical']
        total_usable_bags += cnt
        total_expiring_soon += crit_cnt
        if cnt < 3:
            total_low_stock_groups += 1

        price = Config.BLOOD_PRICES.get(bg, 2500)
        
        summary.append({
            'blood_group': bg,
            'available_count': cnt,
            'good_count': good_cnt,
            'critical_count': crit_cnt,
            'is_low_stock': cnt < 3,
            'is_out_of_stock': cnt == 0,
            'price_per_unit': price
        })

    # Overall inventory statistics
    total_pending_screening = db.blood_bags.count_documents({'status': 'Pending Screening'})
    total_issued = db.blood_bags.count_documents({'status': 'Issued'})
    total_expired = db.blood_bags.count_documents({
        '$or': [
            {'status': 'Expired'},
            {'status': 'Available', 'expiry_date': {'$lt': now}}
        ]
    })
    total_collected = db.blood_bags.count_documents({})

    return jsonify({
        'success': True,
        'timestamp': now.isoformat(),
        'total_usable_bags': total_usable_bags,
        'total_expiring_soon': total_expiring_soon,
        'total_pending_screening': total_pending_screening,
        'total_low_stock_groups': total_low_stock_groups,
        'total_issued_bags': total_issued,
        'total_expired_bags': total_expired,
        'total_collected_bags': total_collected,
        'groups': summary
    })


@stock_bp.route('/api/stock/bags', methods=['GET'])
@login_required
def list_blood_bags():
    """
    List individual blood bags with composite $and filtering:
    - blood_group
    - status (Available, Pending Screening, Issued, Expired, All)
    - search keyword combined safely using $and with status filters
    - sorted by expiry_date (FEFO - First Expiry, First Out)
    """
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    blood_group = request.args.get('blood_group')
    status = request.args.get('status')
    search = request.args.get('search')
    now = datetime.now()

    and_conditions = []

    if blood_group and blood_group != 'ALL':
        and_conditions.append({'blood_group': blood_group})

    if status and status != 'ALL':
        if status == 'Expired':
            and_conditions.append({
                '$or': [
                    {'status': 'Expired'},
                    {'status': 'Available', 'expiry_date': {'$lt': now}}
                ]
            })
        elif status == 'Available':
            and_conditions.append({'status': 'Available', 'expiry_date': {'$gte': now}})
        else:
            and_conditions.append({'status': status})

    if search:
        and_conditions.append({
            '$or': [
                {'bag_id': {'$regex': search, '$options': 'i'}},
                {'donor_name': {'$regex': search, '$options': 'i'}},
                {'donor_id': {'$regex': search, '$options': 'i'}},
                {'storage_location': {'$regex': search, '$options': 'i'}},
                {'issued_to_hospital_name': {'$regex': search, '$options': 'i'}}
            ]
        })

    final_query = {'$and': and_conditions} if and_conditions else {}
    bags = list(db.blood_bags.find(final_query).sort('expiry_date', 1))

    # Calculate live expiry indicators
    for b in bags:
        exp = b.get('expiry_date')
        if isinstance(exp, str):
            try:
                exp_dt = datetime.fromisoformat(exp.replace("Z", ""))
            except Exception:
                exp_dt = None
        else:
            exp_dt = exp

        if exp_dt:
            delta = (exp_dt - now).days
            b['days_until_expiry'] = delta
            b['is_expired'] = delta < 0
            b['is_critical_expiry'] = (0 <= delta <= 7)
        else:
            b['days_until_expiry'] = 35
            b['is_expired'] = False
            b['is_critical_expiry'] = False

    return jsonify({
        'success': True,
        'count': len(bags),
        'bags': serialize_doc(bags)
    })


@stock_bp.route('/api/stock/<bag_id>/timeline', methods=['GET'])
@login_required
def get_bag_timeline(bag_id):
    """
    Complete audit timeline and traceability for an individual blood unit:
    Collection -> Pathogen Screening -> Storage / FEFO Queue -> Allocation -> Dispatched Invoice.
    """
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    bag = db.blood_bags.find_one({'bag_id': bag_id})
    if not bag:
        return jsonify({'success': False, 'message': f'Blood bag {bag_id} not found'}), 404

    donor = db.donors.find_one({'donor_id': bag.get('donor_id')})
    request_doc = db.blood_requests.find_one({'request_id': bag.get('request_id')}) if bag.get('request_id') else None
    invoice_doc = db.invoices.find_one({'blood_bags': bag_id}) if bag.get('status') == 'Issued' else None

    # Construct complete chronological audit milestones
    milestones = []
    
    # 1. Collection
    milestones.append({
        'stage': 'Collection',
        'title': f'Collected {bag.get("volume_ml", 450)}ml from Donor {bag.get("donor_name", "Registered Donor")}',
        'timestamp': bag.get('collection_date'),
        'actor': bag.get('collected_by', 'Blood Collection Staff'),
        'badge': 'success',
        'icon': 'fa-hand-holding-droplet'
    })

    # 2. Screening
    screening_status = bag.get('screening_status', 'Pending')
    milestones.append({
        'stage': 'Pathogen Screening',
        'title': f'Viral Screening Result: {screening_status}',
        'timestamp': bag.get('screened_at') or bag.get('collection_date'),
        'actor': bag.get('screened_by', 'Clinical Lab'),
        'badge': 'success' if screening_status == 'PASSED' else ('warning' if screening_status == 'Pending' else 'danger'),
        'icon': 'fa-microscope',
        'details': bag.get('screening_details')
    })

    # 3. Storage
    milestones.append({
        'stage': 'Inventory Storage',
        'title': f'Stored at {bag.get("storage_location", "Main Cold Storage")} (Expiry: {bag.get("expiry_date")})',
        'timestamp': bag.get('screened_at') or bag.get('collection_date'),
        'actor': 'Inventory System',
        'badge': 'info',
        'icon': 'fa-temperature-low'
    })

    # 4. Allocation / Issue
    if bag.get('status') == 'Issued':
        milestones.append({
            'stage': 'Dispatch & Issue',
            'title': f'Issued to {bag.get("issued_to_hospital_name", "Hospital")} for Request {bag.get("request_id")}',
            'timestamp': bag.get('issued_date'),
            'actor': 'Super Admin (FEFO)',
            'badge': 'primary',
            'icon': 'fa-truck-medical',
            'invoice_number': invoice_doc.get('invoice_number') if invoice_doc else None
        })

    return jsonify({
        'success': True,
        'bag': serialize_doc(bag),
        'donor': serialize_doc(donor),
        'request': serialize_doc(request_doc),
        'invoice': serialize_doc(invoice_doc),
        'timeline': serialize_doc(milestones),
        'qr_payload': f"BLOOD-BANK|BAG:{bag_id}|GRP:{bag.get('blood_group')}|EXP:{str(bag.get('expiry_date'))[:10]}"
    })
