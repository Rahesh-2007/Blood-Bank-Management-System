from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
from database import get_db, get_next_sequence, serialize_doc
from models.helpers import (
    check_donor_eligibility, login_required, role_required,
    get_session_user, log_activity, validate_date_string, BLOOD_GROUPS
)

donor_bp = Blueprint('donor_bp', __name__)

@donor_bp.route('/api/donors', methods=['GET'])
@login_required
def list_donors():
    """
    List registered blood donors:
    - Recalculates dynamic clinical eligibility in real-time based on today's date.
    - Accurately filters by current eligibility status and blood group.
    """
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not available'}), 503

    blood_group = request.args.get('blood_group')
    eligible_filter = request.args.get('eligible')
    status_filter = request.args.get('status')
    search = request.args.get('search')

    query = {}
    if blood_group and blood_group != 'ALL':
        query['blood_group'] = blood_group
    if status_filter and status_filter != 'ALL':
        query['status'] = status_filter

    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'donor_id': {'$regex': search, '$options': 'i'}},
            {'contact': {'$regex': search, '$options': 'i'}},
            {'email': {'$regex': search, '$options': 'i'}}
        ]

    donors = list(db.donors.find(query).sort('created_at', -1))

    # Re-evaluate dynamic eligibility in real-time for each donor
    evaluated_donors = []
    for d in donors:
        is_active = (d.get('status', 'Active') == 'Active')
        is_el, reasons, next_eligible_date = check_donor_eligibility(
            age=d.get('age', 0),
            weight=d.get('weight', 0),
            has_health_issues=d.get('has_health_issues', False),
            last_donation_date=d.get('last_donation_date'),
            is_active=is_active
        )
        d['current_eligible'] = is_el
        d['eligible'] = is_el  # Synchronize
        d['eligibility_reasons'] = reasons
        d['next_eligible_date'] = next_eligible_date

        # Apply eligibility filter if specified
        if eligible_filter is not None and eligible_filter != '' and eligible_filter != 'ALL':
            target_bool = (eligible_filter.lower() == 'true')
            if is_el == target_bool:
                evaluated_donors.append(d)
        else:
            evaluated_donors.append(d)

    return jsonify({
        'success': True,
        'count': len(evaluated_donors),
        'donors': serialize_doc(evaluated_donors)
    })


@donor_bp.route('/api/donors/check-eligibility', methods=['POST'])
def test_eligibility():
    """Live interactive eligibility feedback endpoint."""
    data = request.get_json() or {}
    age = data.get('age')
    weight = data.get('weight')
    has_health_issues = bool(data.get('has_health_issues', False))
    last_donation_date = data.get('last_donation_date')

    is_eligible, reasons, next_date = check_donor_eligibility(
        age=age,
        weight=weight,
        has_health_issues=has_health_issues,
        last_donation_date=last_donation_date
    )

    return jsonify({
        'success': True,
        'is_eligible': is_eligible,
        'reasons': reasons,
        'next_eligible_date': next_date
    })


@donor_bp.route('/api/donors/register', methods=['POST'])
@login_required
@role_required(['COORDINATOR', 'ADMIN'])
def register_donor():
    session_user = get_session_user()
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    age = data.get('age')
    gender = data.get('gender', 'Male')
    blood_group = data.get('blood_group', '').strip().upper()
    contact = data.get('contact', '').strip()
    email = data.get('email', '').strip()
    weight = data.get('weight')
    has_health_issues = bool(data.get('has_health_issues', False))
    health_notes = data.get('health_notes', '').strip()
    last_donation_date = data.get('last_donation_date')

    if not name or age is None or not blood_group or weight is None:
        return jsonify({'success': False, 'message': 'Full Name, Age, Blood Group, and Weight are mandatory fields'}), 400

    if blood_group not in BLOOD_GROUPS:
        return jsonify({'success': False, 'message': f'Invalid blood group: {blood_group}. Allowed: {", ".join(BLOOD_GROUPS)}'}), 400

    # Validate age
    try:
        age_int = int(age)
        if age_int < 18 or age_int > 60:
            return jsonify({'success': False, 'message': f'Donor age must be between 18 and 60 years (Provided: {age_int})'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Age must be a valid whole number'}), 400

    # Validate weight
    try:
        weight_flt = float(weight)
        if weight_flt < 45.0 or weight_flt > 250.0:
            return jsonify({'success': False, 'message': f'Donor weight must be at least 45 kg (Provided: {weight_flt} kg)'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Weight must be a valid number'}), 400

    # Validate last donation date if provided
    parsed_last_date_str = None
    if last_donation_date:
        valid, parsed_dt = validate_date_string(last_donation_date, "Last Donation Date")
        if not valid:
            return jsonify({'success': False, 'message': parsed_dt}), 400
        parsed_last_date_str = parsed_dt.strftime('%Y-%m-%d')

    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    # Evaluate clinical eligibility
    is_eligible, reasons, next_date = check_donor_eligibility(
        age=age_int,
        weight=weight_flt,
        has_health_issues=has_health_issues,
        last_donation_date=parsed_last_date_str,
        is_active=True
    )

    donor_id = get_next_sequence('donor_seq', prefix='DON', start_val=1001)

    donor_doc = {
        'donor_id': donor_id,
        'name': name,
        'age': age_int,
        'gender': gender,
        'blood_group': blood_group,
        'contact': contact,
        'email': email,
        'weight': weight_flt,
        'has_health_issues': has_health_issues,
        'health_notes': health_notes,
        'last_donation_date': parsed_last_date_str,
        'eligible': is_eligible,
        'eligibility_reasons': reasons,
        'next_eligible_date': next_date,
        'total_donations': 0,
        'status': 'Active',  # Active | Deactivated
        'registered_by': session_user.get('name', 'Staff'),
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }

    db.donors.insert_one(donor_doc)
    log_activity(db, session_user.get('user_id') or session_user.get('coordinator_id'), session_user.get('name'), session_user.get('role'), 'REGISTER_DONOR', f'Registered donor {name} [{donor_id}] - {blood_group}', target_type='DONOR', target_id=donor_id)

    return jsonify({
        'success': True,
        'message': f'Donor {name} registered successfully with ID {donor_id}',
        'donor': serialize_doc(donor_doc)
    }), 201


@donor_bp.route('/api/donors/<donor_id>', methods=['GET'])
@login_required
def get_donor_detail(donor_id):
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database error'}), 503

    donor = db.donors.find_one({'donor_id': donor_id})
    if not donor:
        return jsonify({'success': False, 'message': 'Donor not found'}), 404

    # Fetch donor's past donation history
    donations = list(db.blood_bags.find({'donor_id': donor_id}).sort('collection_date', -1))

    is_active = (donor.get('status', 'Active') == 'Active')
    is_el, reasons, next_date = check_donor_eligibility(
        age=donor.get('age', 0),
        weight=donor.get('weight', 0),
        has_health_issues=donor.get('has_health_issues', False),
        last_donation_date=donor.get('last_donation_date'),
        is_active=is_active
    )

    donor_data = serialize_doc(donor)
    donor_data['current_eligible'] = is_el
    donor_data['eligibility_reasons'] = reasons
    donor_data['next_eligible_date'] = next_date

    return jsonify({
        'success': True,
        'donor': donor_data,
        'donations': serialize_doc(donations)
    })


@donor_bp.route('/api/donors/<donor_id>', methods=['PUT'])
@login_required
@role_required(['COORDINATOR', 'ADMIN'])
def edit_donor_profile(donor_id):
    """
    Update donor personal details while preserving complete historical donation records.
    """
    session_user = get_session_user()
    data = request.get_json() or {}
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    donor = db.donors.find_one({'donor_id': donor_id})
    if not donor:
        return jsonify({'success': False, 'message': f'Donor {donor_id} not found'}), 404

    name = data.get('name', donor.get('name')).strip()
    contact = data.get('contact', donor.get('contact')).strip()
    email = data.get('email', donor.get('email')).strip()
    health_notes = data.get('health_notes', donor.get('health_notes')).strip()
    has_health_issues = bool(data.get('has_health_issues', donor.get('has_health_issues', False)))

    update_fields = {
        'name': name,
        'contact': contact,
        'email': email,
        'health_notes': health_notes,
        'has_health_issues': has_health_issues,
        'updated_at': datetime.now()
    }

    if 'age' in data:
        try:
            update_fields['age'] = int(data['age'])
        except Exception:
            pass

    if 'weight' in data:
        try:
            update_fields['weight'] = float(data['weight'])
        except Exception:
            pass

    if 'gender' in data:
        update_fields['gender'] = data['gender']

    # Recalculate eligibility with updated profile values
    is_el, reasons, next_date = check_donor_eligibility(
        age=update_fields.get('age', donor.get('age')),
        weight=update_fields.get('weight', donor.get('weight')),
        has_health_issues=has_health_issues,
        last_donation_date=donor.get('last_donation_date'),
        is_active=(donor.get('status', 'Active') == 'Active')
    )

    update_fields['eligible'] = is_el
    update_fields['eligibility_reasons'] = reasons
    update_fields['next_eligible_date'] = next_date

    db.donors.update_one({'donor_id': donor_id}, {'$set': update_fields})
    log_activity(db, session_user.get('user_id') or session_user.get('coordinator_id'), session_user.get('name'), session_user.get('role'), 'EDIT_DONOR', f'Updated profile for donor {name} [{donor_id}]', target_type='DONOR', target_id=donor_id)

    return jsonify({
        'success': True,
        'message': f'Donor {name} updated successfully!',
        'donor': serialize_doc(db.donors.find_one({'donor_id': donor_id}))
    })


@donor_bp.route('/api/donors/<donor_id>/status', methods=['POST'])
@login_required
@role_required(['COORDINATOR', 'ADMIN'])
def toggle_donor_status(donor_id):
    """
    Activate or deactivate donor account.
    """
    session_user = get_session_user()
    data = request.get_json() or {}
    new_status = data.get('status', 'Active').strip().capitalize()
    if new_status not in ['Active', 'Deactivated']:
        new_status = 'Active'

    db = get_db()
    donor = db.donors.find_one({'donor_id': donor_id})
    if not donor:
        return jsonify({'success': False, 'message': 'Donor not found'}), 404

    db.donors.update_one({'donor_id': donor_id}, {'$set': {'status': new_status, 'updated_at': datetime.now()}})
    log_activity(db, session_user.get('user_id') or session_user.get('coordinator_id'), session_user.get('name'), session_user.get('role'), 'DONOR_STATUS', f'Donor {donor_id} status set to {new_status}', target_type='DONOR', target_id=donor_id)

    return jsonify({
        'success': True,
        'message': f'Donor {donor.get("name")} status updated to {new_status}.',
        'status': new_status
    })
