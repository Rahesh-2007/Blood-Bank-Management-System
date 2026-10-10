from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
from database import get_db, get_next_sequence, serialize_doc
from config import Config
from models.helpers import (
    check_donor_eligibility, login_required, role_required,
    get_session_user, log_activity
)

donation_bp = Blueprint('donation_bp', __name__)

@donation_bp.route('/api/donations/record', methods=['POST'])
@login_required
@role_required(['COORDINATOR', 'ADMIN'])
def record_donation():
    """
    Record Blood Donation & Initiate Screening Workflow:
    - Concurrency protection: verifies donor is active & eligible atomically.
    - Creates blood bag as 'Pending Screening' with unique BAG10001... ID.
    - Sets Expiry = Collection Date + 35 days.
    - Sets Donor's last_donation_date to now, and recalculates eligibility for next 120 days.
    """
    session_user = get_session_user()
    data = request.get_json() or {}
    donor_id = data.get('donor_id', '').strip()
    storage_location = data.get('storage_location', 'Cold Room A - Quarantine Rack').strip()
    collected_by = session_user.get('name', 'Blood Collection Staff')

    try:
        volume_ml = int(data.get('volume_ml', 450))
        if volume_ml not in [350, 450, 500]:
            volume_ml = 450
    except (ValueError, TypeError):
        volume_ml = 450

    if not donor_id:
        return jsonify({'success': False, 'message': 'Donor selection is required'}), 400

    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    donor = db.donors.find_one({'donor_id': donor_id})
    if not donor:
        return jsonify({'success': False, 'message': f'Donor {donor_id} not found'}), 404

    is_active = (donor.get('status', 'Active') == 'Active')
    if not is_active:
        return jsonify({'success': False, 'message': 'Cannot record donation for a deactivated donor'}), 400

    # Clinical Eligibility Check
    is_eligible, reasons, next_date = check_donor_eligibility(
        age=donor.get('age', 0),
        weight=donor.get('weight', 0),
        has_health_issues=donor.get('has_health_issues', False),
        last_donation_date=donor.get('last_donation_date'),
        is_active=is_active
    )

    if not is_eligible:
        return jsonify({
            'success': False,
            'message': 'Donor is currently NOT eligible to donate blood.',
            'reasons': reasons,
            'next_eligible_date': next_date
        }), 400

    now = datetime.now()
    collection_date = now
    expiry_date = collection_date + timedelta(days=Config.BLOOD_SHELF_LIFE_DAYS)

    blood_group = donor.get('blood_group')
    selling_price = Config.BLOOD_PRICES.get(blood_group, 2500)

    # Concurrency Protection: Atomic update donor last donation date before bag creation
    next_eligible_calc = (collection_date + timedelta(days=Config.MIN_DONATION_INTERVAL_DAYS)).strftime('%Y-%m-%d')
    updated_donor = db.donors.find_one_and_update(
        {
            'donor_id': donor_id,
            'status': 'Active'
        },
        {
            '$set': {
                'last_donation_date': collection_date.strftime('%Y-%m-%d'),
                'eligible': False,
                'eligibility_reasons': [f"Donated on {collection_date.strftime('%d-%b-%Y')}. Next eligible in 120 days ({next_eligible_calc})."],
                'next_eligible_date': next_eligible_calc,
                'updated_at': now
            },
            '$inc': {'total_donations': 1}
        },
        return_document=True
    )

    if not updated_donor:
        return jsonify({'success': False, 'message': 'Concurrent donation record conflict or donor inactive.'}), 409

    # Generate sequential Bag ID
    bag_id = get_next_sequence('blood_bag_seq', prefix='BAG', start_val=10001)

    blood_bag = {
        'bag_id': bag_id,
        'blood_group': blood_group,
        'donor_id': donor_id,
        'donor_name': donor.get('name'),
        'donor_contact': donor.get('contact'),
        'collection_date': collection_date,
        'expiry_date': expiry_date,
        'volume_ml': volume_ml,
        'storage_location': storage_location,
        'status': 'Pending Screening',  # Pending Screening | Available | Issued | Expired | Discarded
        'screening_status': 'Pending',   # Pending | PASSED | FAILED
        'screening_details': None,
        'screened_by': None,
        'screened_at': None,
        'selling_price': selling_price,
        'collected_by': collected_by,
        'issued_to_hospital_id': None,
        'issued_to_hospital_name': None,
        'issued_date': None,
        'request_id': None,
        'created_at': now
    }

    db.blood_bags.insert_one(blood_bag)
    log_activity(db, session_user.get('user_id') or session_user.get('coordinator_id'), session_user.get('name'), session_user.get('role'), 'RECORD_DONATION', f'Collected {volume_ml}ml {blood_group} blood unit [{bag_id}] from donor {donor.get("name")} (Pending Screening)', target_type='BLOOD_BAG', target_id=bag_id)

    return jsonify({
        'success': True,
        'message': f'Donation recorded successfully! Blood Bag {bag_id} registered and queued for clinical lab screening.',
        'bag': serialize_doc(blood_bag)
    }), 201


@donation_bp.route('/api/donations/screen/<bag_id>', methods=['POST'])
@login_required
@role_required(['COORDINATOR', 'ADMIN'])
def screen_blood_bag(bag_id):
    """
    Clinical Screening & Authorized Release Workflow:
    - Verifies mandatory infectious pathogen tests: HIV, HBV, HCV, Syphilis, Malaria.
    - If PASSED -> status = 'Available' (available for FEFO issuing).
    - If FAILED -> status = 'Discarded' with reason.
    """
    session_user = get_session_user()
    data = request.get_json() or {}
    screening_result = data.get('result', 'PASSED').strip().upper()  # PASSED | FAILED
    notes = data.get('notes', '').strip()
    hiv_test = data.get('hiv_test', 'NEGATIVE').strip().upper()
    hbv_test = data.get('hbv_test', 'NEGATIVE').strip().upper()
    hcv_test = data.get('hcv_test', 'NEGATIVE').strip().upper()
    syphilis_test = data.get('syphilis_test', 'NEGATIVE').strip().upper()
    malaria_test = data.get('malaria_test', 'NEGATIVE').strip().upper()

    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    bag = db.blood_bags.find_one({'bag_id': bag_id})
    if not bag:
        return jsonify({'success': False, 'message': f'Blood Bag {bag_id} not found'}), 404

    if bag.get('status') not in ['Pending Screening', 'Available']:
        return jsonify({'success': False, 'message': f'Cannot screen bag with status: {bag.get("status")}'}), 400

    # Auto-flag as FAILED if any viral marker is POSITIVE
    has_positive_marker = any(test == 'POSITIVE' for test in [hiv_test, hbv_test, hcv_test, syphilis_test, malaria_test])
    if has_positive_marker:
        screening_result = 'FAILED'

    now = datetime.now()
    new_status = 'Available' if screening_result == 'PASSED' else 'Discarded'
    location = 'Main Cold Storage - Usable' if screening_result == 'PASSED' else 'Biohazard Disposal Unit'

    screening_details = {
        'hiv_test': hiv_test,
        'hbv_test': hbv_test,
        'hcv_test': hcv_test,
        'syphilis_test': syphilis_test,
        'malaria_test': malaria_test,
        'notes': notes,
        'screened_by': session_user.get('name', 'Lab Officer'),
        'screened_at': now.isoformat()
    }

    db.blood_bags.update_one(
        {'bag_id': bag_id},
        {
            '$set': {
                'status': new_status,
                'screening_status': screening_result,
                'screening_details': screening_details,
                'storage_location': location,
                'screened_by': session_user.get('name', 'Lab Officer'),
                'screened_at': now,
                'updated_at': now
            }
        }
    )

    msg = f'Blood Bag {bag_id} screening completed: {screening_result}. Status updated to {new_status}.'
    log_activity(db, session_user.get('user_id') or session_user.get('coordinator_id'), session_user.get('name'), session_user.get('role'), 'SCREEN_BLOOD', msg, target_type='BLOOD_BAG', target_id=bag_id)

    return jsonify({
        'success': True,
        'message': msg,
        'bag_id': bag_id,
        'status': new_status,
        'screening_status': screening_result,
        'screening_details': screening_details
    })


@donation_bp.route('/api/donations/history', methods=['GET'])
@login_required
def get_donation_history():
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    donor_id = request.args.get('donor_id')
    blood_group = request.args.get('blood_group')
    filter_today = request.args.get('today')
    filter_pending_screening = request.args.get('pending_screening')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = {}
    if donor_id:
        query['donor_id'] = donor_id
    if blood_group and blood_group != 'ALL':
        query['blood_group'] = blood_group
    if filter_pending_screening and filter_pending_screening.lower() == 'true':
        query['status'] = 'Pending Screening'

    if filter_today and filter_today.lower() == 'true':
        start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        query['collection_date'] = {'$gte': start_of_day}
    elif start_date and end_date:
        try:
            s_dt = datetime.fromisoformat(start_date)
            e_dt = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59)
            query['collection_date'] = {'$gte': s_dt, '$lte': e_dt}
        except Exception:
            pass

    donations = list(db.blood_bags.find(query).sort('collection_date', -1))

    return jsonify({
        'success': True,
        'count': len(donations),
        'donations': serialize_doc(donations)
    })
