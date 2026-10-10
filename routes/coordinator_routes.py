from flask import Blueprint, request, jsonify
from datetime import datetime
from database import get_db, get_next_sequence, serialize_doc
from werkzeug.security import generate_password_hash
from models.helpers import login_required, role_required, sanitize_account_doc, get_session_user, log_activity

coordinator_bp = Blueprint('coordinator_bp', __name__)

@coordinator_bp.route('/api/coordinators', methods=['GET'])
@login_required
@role_required(['ADMIN'])
def list_coordinators():
    """
    Super Admin listing of all coordinators.
    All password hashes are completely removed.
    """
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    search = request.args.get('search')
    status_filter = request.args.get('status')
    query = {}

    if status_filter and status_filter != 'ALL':
        query['status'] = status_filter

    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'coordinator_id': {'$regex': search, '$options': 'i'}},
            {'email': {'$regex': search, '$options': 'i'}},
            {'branch': {'$regex': search, '$options': 'i'}}
        ]

    coordinators = list(db.coordinators.find(query).sort('created_at', -1))

    cleaned = []
    for c in coordinators:
        c_ser = sanitize_account_doc(serialize_doc(c))
        cleaned.append(c_ser)

    return jsonify({
        'success': True,
        'count': len(cleaned),
        'coordinators': cleaned
    })


@coordinator_bp.route('/api/coordinators/add', methods=['POST'])
@login_required
@role_required(['ADMIN'])
def add_coordinator():
    """
    Super Admin directly creates an active Coordinator account.
    """
    session_user = get_session_user()
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    branch = data.get('branch', 'Main Blood Bank Center').strip()
    phone = data.get('phone', '').strip()
    designation = data.get('designation', 'Blood Collection Officer').strip()

    if not name or not email or not password:
        return jsonify({'success': False, 'message': 'Name, Email, and Password are required'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters long'}), 400

    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    existing = db.coordinators.find_one({'email': email})
    if existing:
        return jsonify({'success': False, 'message': f'Staff member with email {email} already exists'}), 400

    coord_id = get_next_sequence('coord_seq', prefix='COORD', start_val=101)

    coordinator_doc = {
        'coordinator_id': coord_id,
        'name': name,
        'email': email,
        'password': generate_password_hash(password),
        'branch': branch,
        'designation': designation,
        'phone': phone,
        'status': 'ACTIVE',
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }

    db.coordinators.insert_one(coordinator_doc)
    log_activity(db, session_user.get('user_id', 'ADMIN'), session_user.get('name', 'Admin'), 'ADMIN', 'ADD_COORDINATOR', f'Created staff account {name} [{coord_id}] for {branch}', target_type='COORDINATOR', target_id=coord_id)

    return jsonify({
        'success': True,
        'message': f'Blood Bank Staff member {name} registered with ID {coord_id}',
        'coordinator': sanitize_account_doc(serialize_doc(coordinator_doc))
    }), 201


@coordinator_bp.route('/api/coordinators/<coordinator_id>/status', methods=['POST'])
@login_required
@role_required(['ADMIN'])
def update_coordinator_status(coordinator_id):
    """
    Super Admin approves pending coordinator registrations or suspends/activates existing accounts.
    """
    session_user = get_session_user()
    data = request.get_json() or {}
    new_status = data.get('status', 'ACTIVE').strip().upper()  # ACTIVE | PENDING_APPROVAL | SUSPENDED

    if new_status not in ['ACTIVE', 'PENDING_APPROVAL', 'SUSPENDED']:
        return jsonify({'success': False, 'message': 'Invalid status. Use ACTIVE or SUSPENDED.'}), 400

    db = get_db()
    coord = db.coordinators.find_one({'coordinator_id': coordinator_id})
    if not coord:
        return jsonify({'success': False, 'message': 'Staff member not found'}), 404

    db.coordinators.update_one(
        {'coordinator_id': coordinator_id},
        {'$set': {'status': new_status, 'updated_at': datetime.now()}}
    )

    action_label = 'APPROVED' if new_status == 'ACTIVE' else new_status
    msg = f'Staff member {coord.get("name")} [{coordinator_id}] status set to {new_status}.'
    log_activity(db, session_user.get('user_id', 'ADMIN'), session_user.get('name', 'Admin'), 'ADMIN', 'COORDINATOR_APPROVAL', msg, target_type='COORDINATOR', target_id=coordinator_id)

    return jsonify({
        'success': True,
        'message': msg,
        'status': new_status
    })
