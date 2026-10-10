from flask import Blueprint, request, jsonify
from datetime import datetime
from database import get_db, get_next_sequence, serialize_doc
from werkzeug.security import generate_password_hash
from models.helpers import login_required, role_required, sanitize_account_doc, get_session_user, log_activity

hospital_bp = Blueprint('hospital_bp', __name__)

@hospital_bp.route('/api/hospitals', methods=['GET'])
@login_required
@role_required(['ADMIN'])
def list_hospitals():
    """
    Super Admin listing of all registered hospitals.
    All password hashes are stripped from the response.
    """
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    search = request.args.get('search')
    query = {}
    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'hospital_id': {'$regex': search, '$options': 'i'}},
            {'email': {'$regex': search, '$options': 'i'}}
        ]

    hospitals = list(db.hospitals.find(query).sort('created_at', -1))

    cleaned = []
    for h in hospitals:
        hid = h.get('hospital_id')
        h_ser = sanitize_account_doc(serialize_doc(h))
        h_ser['total_requests'] = db.blood_requests.count_documents({'hospital_id': hid})
        h_ser['pending_requests'] = db.blood_requests.count_documents({'hospital_id': hid, 'status': {'$in': ['Pending', 'Partially Approved']}})
        h_ser['total_invoices'] = db.invoices.count_documents({'hospital_id': hid})
        h_ser['unpaid_invoices'] = db.invoices.count_documents({'hospital_id': hid, 'status': 'PENDING'})
        cleaned.append(h_ser)

    return jsonify({
        'success': True,
        'count': len(cleaned),
        'hospitals': cleaned
    })


@hospital_bp.route('/api/hospitals/add', methods=['POST'])
@login_required
@role_required(['ADMIN'])
def add_hospital():
    """
    Super Admin manually registers a new hospital account.
    """
    session_user = get_session_user()
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    phone = data.get('phone', '').strip()
    address = data.get('address', '').strip()
    
    try:
        initial_balance = float(data.get('initial_balance', 0.0))
    except (ValueError, TypeError):
        initial_balance = 0.0

    if not name or not email or not password:
        return jsonify({'success': False, 'message': 'Hospital Name, Email, and Password are required'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters long'}), 400

    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    existing = db.hospitals.find_one({'email': email})
    if existing:
        return jsonify({'success': False, 'message': f'Hospital with email {email} already exists'}), 400

    hospital_id = get_next_sequence('hospital_seq', prefix='HOSP', start_val=101)

    hospital_doc = {
        'hospital_id': hospital_id,
        'name': name,
        'email': email,
        'password': generate_password_hash(password),
        'phone': phone,
        'address': address,
        'contact_person': data.get('contact_person', name),
        'reg_number': data.get('reg_number', f'REG-MED-{hospital_id}'),
        'status': 'ACTIVE',
        'outstanding_balance': initial_balance,
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }

    db.hospitals.insert_one(hospital_doc)
    log_activity(db, session_user.get('user_id', 'ADMIN'), session_user.get('name', 'Admin'), 'ADMIN', 'ADD_HOSPITAL', f'Created hospital account {name} [{hospital_id}]', target_type='HOSPITAL', target_id=hospital_id)

    return jsonify({
        'success': True,
        'message': f'Hospital {name} registered with ID {hospital_id}',
        'hospital': sanitize_account_doc(serialize_doc(hospital_doc))
    }), 201


@hospital_bp.route('/api/hospitals/<hospital_id>', methods=['GET'])
@login_required
def get_hospital(hospital_id):
    session_user = get_session_user()
    if session_user.get('role') == 'HOSPITAL' and session_user.get('hospital_id') != hospital_id:
        return jsonify({'success': False, 'message': 'Access forbidden'}), 403

    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    hospital = db.hospitals.find_one({'hospital_id': hospital_id})
    if not hospital:
        return jsonify({'success': False, 'message': 'Hospital not found'}), 404

    return jsonify({
        'success': True,
        'hospital': sanitize_account_doc(serialize_doc(hospital))
    })
