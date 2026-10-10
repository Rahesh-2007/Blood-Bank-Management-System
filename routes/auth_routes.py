import re
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from database import get_db, serialize_doc, get_next_sequence
from config import Config
from werkzeug.security import check_password_hash, generate_password_hash
from models.helpers import (
    login_required, role_required, get_session_user,
    sanitize_account_doc, log_activity, validate_date_string
)

auth_bp = Blueprint('auth_bp', __name__)

EMAIL_REGEX = r'^[\w\.-]+@[\w\.-]+\.\w+$'

def find_user_by_email(db, email):
    """Search for a user across Coordinator, Hospital, and Admin collections."""
    email_clean = email.strip().lower()
    
    # 1. Check coordinators
    coord = db.coordinators.find_one({'email': {'$regex': f'^{re.escape(email_clean)}$', '$options': 'i'}})
    if coord:
        return coord, 'COORDINATOR', db.coordinators

    # 2. Check hospitals
    hosp = db.hospitals.find_one({'email': {'$regex': f'^{re.escape(email_clean)}$', '$options': 'i'}})
    if hosp:
        return hosp, 'HOSPITAL', db.hospitals

    # 3. Check general users / admin
    user = db.users.find_one({'email': {'$regex': f'^{re.escape(email_clean)}$', '$options': 'i'}})
    if user:
        return user, user.get('role', 'ADMIN'), db.users

    return None, None, None


@auth_bp.route('/api/auth/register', methods=['POST'])
def register_user():
    """
    Register a new Hospital or Coordinator account.
    - Hospital accounts are registered and activated.
    - Coordinator public signups are created with PENDING_APPROVAL status (requiring Admin activation)
      to prevent unauthorized immediate access to blood collection controls.
    """
    data = request.get_json() or {}
    role = data.get('role', 'HOSPITAL').strip().upper()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()

    if role not in ['HOSPITAL', 'COORDINATOR']:
        return jsonify({'success': False, 'message': 'Invalid role specified. Only Hospital and Coordinator accounts can be registered.'}), 400

    if not email or not password or not name:
        return jsonify({'success': False, 'message': 'Name, email, and password are required.'}), 400

    if not re.match(EMAIL_REGEX, email):
        return jsonify({'success': False, 'message': 'Please provide a valid email address.'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters long.'}), 400

    if confirm_password and password != confirm_password:
        return jsonify({'success': False, 'message': 'Passwords do not match.'}), 400

    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database connection error. Please try again.'}), 503

    # Check for existing email across all account collections
    existing_user, _, _ = find_user_by_email(db, email)
    if existing_user:
        return jsonify({
            'success': False,
            'message': f'An account with email "{email}" is already registered. Please sign in instead.'
        }), 409

    hashed_password = generate_password_hash(password)
    now = datetime.now()

    if role == 'HOSPITAL':
        hospital_id = get_next_sequence('hospital_seq', prefix='HOSP', start_val=101)
        address = data.get('address', '').strip()
        reg_number = data.get('reg_number', '').strip()
        contact_person = data.get('contact_person', name).strip()

        doc = {
            'hospital_id': hospital_id,
            'name': name,
            'email': email,
            'password': hashed_password,
            'phone': phone,
            'address': address,
            'reg_number': reg_number,
            'contact_person': contact_person,
            'status': 'ACTIVE',
            'outstanding_balance': 0.0,
            'notification_prefs': {
                'request_updates': True,
                'invoice_alerts': True,
                'email_notifications': True
            },
            'created_at': now,
            'updated_at': now
        }
        db.hospitals.insert_one(doc)

        session['user'] = {
            'role': 'HOSPITAL',
            'hospital_id': hospital_id,
            'hospital_name': name,
            'name': name,
            'email': email,
            'phone': phone,
            'address': address,
            'status': 'ACTIVE'
        }

        log_activity(db, hospital_id, name, 'HOSPITAL', 'REGISTER', f'Hospital {name} registered account {hospital_id}', target_type='HOSPITAL', target_id=hospital_id)

        return jsonify({
            'success': True,
            'role': 'HOSPITAL',
            'hospital_id': hospital_id,
            'message': f'Hospital account created successfully! Welcome, {name}.',
            'user': session['user'],
            'redirect': '/hospital'
        }), 201

    elif role == 'COORDINATOR':
        # Coordinator public registration requires Admin review before activation
        coordinator_id = get_next_sequence('coord_seq', prefix='COORD', start_val=101)
        branch = data.get('branch', 'Main Blood Bank Center').strip()
        designation = data.get('designation', 'Blood Collection Officer').strip()

        doc = {
            'coordinator_id': coordinator_id,
            'name': name,
            'email': email,
            'password': hashed_password,
            'branch': branch,
            'designation': designation,
            'phone': phone,
            'status': 'PENDING_APPROVAL',  # Requires Super Admin approval
            'notification_prefs': {
                'donor_alerts': True,
                'urgent_needs': True,
                'system_announcements': True
            },
            'created_at': now,
            'updated_at': now
        }
        db.coordinators.insert_one(doc)

        log_activity(db, coordinator_id, name, 'COORDINATOR', 'REGISTER_REQUEST', f'Coordinator {name} submitted registration for branch {branch} (Pending Approval)', target_type='COORDINATOR', target_id=coordinator_id)

        return jsonify({
            'success': True,
            'role': 'COORDINATOR',
            'coordinator_id': coordinator_id,
            'status': 'PENDING_APPROVAL',
            'message': f'Blood Bank Staff registration submitted successfully! Staff ID: {coordinator_id}. Your account is pending Super Admin activation.',
            'redirect': '/'
        }), 201


@auth_bp.route('/api/auth/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400

    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not reachable'}), 503

    user = db.users.find_one({
        'email': {'$regex': f'^{re.escape(email)}$', '$options': 'i'},
        'role': 'ADMIN'
    })

    if not user or not check_password_hash(user.get('password', ''), password):
        return jsonify({'success': False, 'message': 'Invalid Super Admin credentials'}), 401

    session['user'] = {
        'role': 'ADMIN',
        'user_id': user.get('user_id', 'ADMIN01'),
        'name': user.get('name', 'Super Admin'),
        'email': user.get('email'),
        'designation': user.get('designation', 'Global System Administrator'),
        'status': 'ACTIVE'
    }

    log_activity(db, user.get('user_id', 'ADMIN01'), user.get('name', 'Super Admin'), 'ADMIN', 'LOGIN', 'Super Admin signed in')

    return jsonify({
        'success': True,
        'message': f'Welcome back, {user.get("name", "Super Admin")}!',
        'user': session['user'],
        'redirect': '/admin'
    })


@auth_bp.route('/api/auth/coordinator/login', methods=['POST'])
def coordinator_login():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400

    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not reachable'}), 503

    coord = db.coordinators.find_one({
        'email': {'$regex': f'^{re.escape(email)}$', '$options': 'i'}
    })

    if not coord or not check_password_hash(coord.get('password', ''), password):
        return jsonify({'success': False, 'message': 'Invalid Blood Bank Staff credentials'}), 401

    if coord.get('status') == 'PENDING_APPROVAL':
        return jsonify({
            'success': False,
            'message': 'Your staff account is awaiting Super Admin activation. Please contact your administrator.'
        }), 403

    if coord.get('status') == 'SUSPENDED':
        return jsonify({
            'success': False,
            'message': 'This staff account has been suspended. Please contact Super Admin.'
        }), 403

    session['user'] = {
        'role': 'COORDINATOR',
        'coordinator_id': coord.get('coordinator_id'),
        'user_id': coord.get('coordinator_id'),
        'name': coord.get('name'),
        'email': coord.get('email'),
        'branch': coord.get('branch', 'Main Branch'),
        'blood_bank_branch': coord.get('branch', 'Main Branch'),
        'designation': coord.get('designation', 'Blood Collection Officer'),
        'phone': coord.get('phone'),
        'status': coord.get('status', 'ACTIVE')
    }

    log_activity(db, coord.get('coordinator_id'), coord.get('name'), 'COORDINATOR', 'LOGIN', f'Coordinator signed in at branch {coord.get("branch")}')

    return jsonify({
        'success': True,
        'message': f'Welcome, {coord.get("name")}!',
        'user': session['user'],
        'redirect': '/coordinator'
    })


@auth_bp.route('/api/auth/hospital/login', methods=['POST'])
def hospital_login():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    hospital_id = data.get('hospital_id', '').strip()
    password = data.get('password', '').strip()

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400

    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not reachable'}), 503

    query = {'email': {'$regex': f'^{re.escape(email)}$', '$options': 'i'}}
    if hospital_id:
        query['hospital_id'] = {'$regex': f'^{re.escape(hospital_id)}$', '$options': 'i'}

    hosp = db.hospitals.find_one(query)

    if not hosp or not check_password_hash(hosp.get('password', ''), password):
        return jsonify({'success': False, 'message': 'Invalid Hospital credentials'}), 401

    if hosp.get('status') == 'SUSPENDED':
        return jsonify({
            'success': False,
            'message': 'This hospital account has been suspended. Please contact Super Admin.'
        }), 403

    session['user'] = {
        'role': 'HOSPITAL',
        'hospital_id': hosp.get('hospital_id'),
        'user_id': hosp.get('hospital_id'),
        'hospital_name': hosp.get('name'),
        'name': hosp.get('name'),
        'email': hosp.get('email'),
        'phone': hosp.get('phone'),
        'address': hosp.get('address'),
        'reg_number': hosp.get('reg_number'),
        'contact_person': hosp.get('contact_person', hosp.get('name')),
        'status': hosp.get('status', 'ACTIVE')
    }

    log_activity(db, hosp.get('hospital_id'), hosp.get('name'), 'HOSPITAL', 'LOGIN', f'Hospital {hosp.get("name")} signed in')

    return jsonify({
        'success': True,
        'message': f'Welcome, {hosp.get("name")}!',
        'user': session['user'],
        'redirect': '/hospital'
    })


@auth_bp.route('/api/auth/me', methods=['GET'])
def get_current_user_status():
    user = session.get('user')
    if user:
        return jsonify({
            'authenticated': True,
            'user': user
        })
    return jsonify({
        'authenticated': False,
        'user': None
    })


@auth_bp.route('/api/auth/logout', methods=['POST', 'GET'])
def logout():
    user = session.get('user')
    if user:
        db = get_db()
        log_activity(db, user.get('user_id') or user.get('hospital_id') or user.get('coordinator_id'), user.get('name'), user.get('role'), 'LOGOUT', 'User signed out')
    session.clear()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully',
        'redirect': '/'
    })


# ==============================================================================
# PROFILE MANAGEMENT APIS (Super Admin, Coordinator, Hospital)
# ==============================================================================

@auth_bp.route('/api/profile/me', methods=['GET'])
@login_required
def get_profile():
    """
    Returns the authenticated user's complete profile with password hashes excluded.
    Calculates dynamic role-specific activity totals and metrics from ground truth records.
    """
    user = get_session_user()
    role = user.get('role')
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    profile_data = {}
    stats = {}

    if role == 'ADMIN':
        admin_doc = db.users.find_one({'role': 'ADMIN'}) or {}
        profile_data = sanitize_account_doc(admin_doc)
        profile_data['account_id'] = admin_doc.get('user_id', 'ADMIN01')
        profile_data['role'] = 'ADMIN'
        profile_data['role_display'] = 'Super Administrator'
        profile_data['name'] = admin_doc.get('name', 'Super Admin')
        profile_data['email'] = admin_doc.get('email', 'admin@bloodbank.org')
        profile_data['phone'] = admin_doc.get('phone', '+91 11 2345 6789')
        profile_data['designation'] = admin_doc.get('designation', 'Central Operations Director')
        profile_data['department'] = admin_doc.get('department', 'National Blood Transfusion Directorate')
        profile_data['status'] = 'ACTIVE'
        profile_data['created_at'] = admin_doc.get('created_at', datetime(2025, 1, 1).isoformat())

        # Calculated Admin Stats
        stats['total_requests_approved'] = db.blood_requests.count_documents({'status': {'$in': ['Approved', 'Partially Approved']}})
        stats['total_bags_available'] = db.blood_bags.count_documents({'status': 'Available', 'expiry_date': {'$gte': datetime.now()}})
        stats['total_donors_registered'] = db.donors.count_documents({})
        stats['total_invoices_managed'] = db.invoices.count_documents({})

    elif role == 'COORDINATOR':
        coord_id = user.get('coordinator_id') or user.get('user_id')
        coord_doc = db.coordinators.find_one({'coordinator_id': coord_id}) or {}
        profile_data = sanitize_account_doc(coord_doc)
        profile_data['account_id'] = coord_id
        profile_data['role'] = 'COORDINATOR'
        profile_data['role_display'] = 'Blood Bank Staff'
        profile_data['branch'] = coord_doc.get('branch', 'Main Center')
        profile_data['designation'] = coord_doc.get('designation', 'Blood Collection Officer')
        profile_data['status'] = coord_doc.get('status', 'ACTIVE')

        # Calculated Coordinator Stats
        stats['donations_recorded'] = db.blood_bags.count_documents({'collected_by': {'$regex': coord_doc.get('name', ''), '$options': 'i'}}) if coord_doc.get('name') else db.blood_bags.count_documents({})
        stats['donors_registered'] = db.donors.count_documents({})
        stats['screening_conducted'] = db.blood_bags.count_documents({'screening_status': {'$in': ['PASSED', 'FAILED']}})

    elif role == 'HOSPITAL':
        hosp_id = user.get('hospital_id') or user.get('user_id')
        hosp_doc = db.hospitals.find_one({'hospital_id': hosp_id}) or {}
        profile_data = sanitize_account_doc(hosp_doc)
        profile_data['account_id'] = hosp_id
        profile_data['role'] = 'HOSPITAL'
        profile_data['role_display'] = 'Hospital Authority'
        profile_data['status'] = hosp_doc.get('status', 'ACTIVE')
        profile_data['contact_person'] = hosp_doc.get('contact_person', hosp_doc.get('name'))
        profile_data['reg_number'] = hosp_doc.get('reg_number', f'REG-MED-{hosp_id}')

        # Calculated Hospital Stats
        invoices = list(db.invoices.find({'hospital_id': hosp_id}))
        total_billed = sum(i.get('total_amount', 0) for i in invoices)
        total_paid = sum(i.get('total_amount', 0) for i in invoices if i.get('status') == 'PAID')
        outstanding = total_billed - total_paid

        stats['total_requests'] = db.blood_requests.count_documents({'hospital_id': hosp_id})
        stats['active_requests'] = db.blood_requests.count_documents({'hospital_id': hosp_id, 'status': {'$in': ['Pending', 'Partially Approved']}})
        stats['total_invoices'] = len(invoices)
        stats['unpaid_invoices'] = sum(1 for i in invoices if i.get('status') == 'PENDING')
        stats['outstanding_balance'] = round(outstanding, 2)
        profile_data['outstanding_balance'] = round(outstanding, 2)

    # Fetch recent activity logs for this user
    account_id = profile_data.get('account_id')
    recent_logs = list(db.activity_logs.find({
        '$or': [
            {'actor_id': account_id},
            {'target_id': account_id}
        ]
    }).sort('timestamp', -1).limit(10))

    return jsonify({
        'success': True,
        'profile': serialize_doc(profile_data),
        'stats': stats,
        'recent_activity': serialize_doc(recent_logs)
    })


@auth_bp.route('/api/profile/me', methods=['PUT'])
@login_required
def update_profile():
    """
    Update editable personal and organization profile details.
    Read-only fields (account ID, role, joining date, status, outstanding balance) are protected on the server.
    """
    user = get_session_user()
    role = user.get('role')
    data = request.get_json() or {}
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    now = datetime.now()
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()

    if not name:
        return jsonify({'success': False, 'message': 'Name cannot be empty'}), 400

    if role == 'ADMIN':
        user_id = user.get('user_id', 'ADMIN01')
        designation = data.get('designation', 'Super Admin').strip()
        department = data.get('department', 'Central Directorate').strip()
        
        db.users.update_one(
            {'role': 'ADMIN'},
            {
                '$set': {
                    'name': name,
                    'phone': phone,
                    'designation': designation,
                    'department': department,
                    'updated_at': now
                }
            }
        )
        session['user']['name'] = name
        session['user']['phone'] = phone

    elif role == 'COORDINATOR':
        coord_id = user.get('coordinator_id') or user.get('user_id')
        designation = data.get('designation', 'Blood Collection Officer').strip()
        
        # Branch is read-only for coordinator (can only be updated by Super Admin)
        db.coordinators.update_one(
            {'coordinator_id': coord_id},
            {
                '$set': {
                    'name': name,
                    'phone': phone,
                    'designation': designation,
                    'updated_at': now
                }
            }
        )
        session['user']['name'] = name
        session['user']['phone'] = phone

    elif role == 'HOSPITAL':
        hosp_id = user.get('hospital_id') or user.get('user_id')
        address = data.get('address', '').strip()
        contact_person = data.get('contact_person', name).strip()
        billing_address = data.get('billing_address', address).strip()

        db.hospitals.update_one(
            {'hospital_id': hosp_id},
            {
                '$set': {
                    'name': name,
                    'phone': phone,
                    'address': address,
                    'contact_person': contact_person,
                    'billing_address': billing_address,
                    'updated_at': now
                }
            }
        )
        session['user']['name'] = name
        session['user']['hospital_name'] = name
        session['user']['phone'] = phone
        session['user']['address'] = address

    account_id = user.get('hospital_id') or user.get('coordinator_id') or user.get('user_id')
    log_activity(db, account_id, name, role, 'UPDATE_PROFILE', f'{role} profile details updated')

    return jsonify({
        'success': True,
        'message': 'Profile updated successfully!',
        'user': session['user']
    })


@auth_bp.route('/api/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """
    Secure password update: verifies current password, requires confirmed new password.
    """
    user = get_session_user()
    role = user.get('role')
    data = request.get_json() or {}
    current_pw = data.get('current_password', '').strip()
    new_pw = data.get('new_password', '').strip()
    confirm_pw = data.get('confirm_password', '').strip()

    if not current_pw or not new_pw:
        return jsonify({'success': False, 'message': 'Current password and new password are required'}), 400

    if len(new_pw) < 6:
        return jsonify({'success': False, 'message': 'New password must be at least 6 characters long'}), 400

    if confirm_pw and new_pw != confirm_pw:
        return jsonify({'success': False, 'message': 'New password confirmation does not match'}), 400

    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    # Fetch existing account doc
    if role == 'ADMIN':
        account = db.users.find_one({'role': 'ADMIN'})
        collection = db.users
        query = {'role': 'ADMIN'}
    elif role == 'COORDINATOR':
        coord_id = user.get('coordinator_id') or user.get('user_id')
        account = db.coordinators.find_one({'coordinator_id': coord_id})
        collection = db.coordinators
        query = {'coordinator_id': coord_id}
    elif role == 'HOSPITAL':
        hosp_id = user.get('hospital_id') or user.get('user_id')
        account = db.hospitals.find_one({'hospital_id': hosp_id})
        collection = db.hospitals
        query = {'hospital_id': hosp_id}
    else:
        return jsonify({'success': False, 'message': 'Unrecognized role'}), 400

    if not account or not check_password_hash(account.get('password', ''), current_pw):
        return jsonify({'success': False, 'message': 'Incorrect current password. Please try again.'}), 400

    new_hash = generate_password_hash(new_pw)
    collection.update_one(query, {'$set': {'password': new_hash, 'updated_at': datetime.now()}})

    account_id = user.get('hospital_id') or user.get('coordinator_id') or user.get('user_id')
    log_activity(db, account_id, user.get('name'), role, 'CHANGE_PASSWORD', 'Account security password changed successfully')

    return jsonify({
        'success': True,
        'message': 'Password changed successfully! Next login will require your new password.'
    })


@auth_bp.route('/api/profile/change-email', methods=['POST'])
@login_required
def change_email():
    """
    Change account email address with verification check and uniqueness validation.
    """
    user = get_session_user()
    role = user.get('role')
    data = request.get_json() or {}
    new_email = data.get('new_email', '').strip().lower()
    password = data.get('password', '').strip()

    if not new_email or not re.match(EMAIL_REGEX, new_email):
        return jsonify({'success': False, 'message': 'Please provide a valid email address'}), 400

    if not password:
        return jsonify({'success': False, 'message': 'Password is required to authorize email change'}), 400

    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database not connected'}), 503

    # Check password authorization
    if role == 'ADMIN':
        account = db.users.find_one({'role': 'ADMIN'})
        collection = db.users
        query = {'role': 'ADMIN'}
    elif role == 'COORDINATOR':
        coord_id = user.get('coordinator_id') or user.get('user_id')
        account = db.coordinators.find_one({'coordinator_id': coord_id})
        collection = db.coordinators
        query = {'coordinator_id': coord_id}
    elif role == 'HOSPITAL':
        hosp_id = user.get('hospital_id') or user.get('user_id')
        account = db.hospitals.find_one({'hospital_id': hosp_id})
        collection = db.hospitals
        query = {'hospital_id': hosp_id}
    else:
        return jsonify({'success': False, 'message': 'Unrecognized role'}), 400

    if not account or not check_password_hash(account.get('password', ''), password):
        return jsonify({'success': False, 'message': 'Incorrect password'}), 401

    # Ensure new email isn't taken by another account
    existing_user, _, _ = find_user_by_email(db, new_email)
    if existing_user and existing_user.get('email', '').lower() != account.get('email', '').lower():
        return jsonify({'success': False, 'message': f'The email "{new_email}" is already registered to another account.'}), 409

    old_email = account.get('email')
    collection.update_one(query, {'$set': {'email': new_email, 'updated_at': datetime.now()}})
    session['user']['email'] = new_email

    account_id = user.get('hospital_id') or user.get('coordinator_id') or user.get('user_id')
    log_activity(db, account_id, user.get('name'), role, 'CHANGE_EMAIL', f'Email changed from {old_email} to {new_email}')

    return jsonify({
        'success': True,
        'message': f'Email updated successfully to {new_email}!',
        'new_email': new_email
    })


@auth_bp.route('/api/profile/notifications', methods=['POST'])
@login_required
def update_notification_preferences():
    """
    Save user notification and alert preferences.
    """
    user = get_session_user()
    role = user.get('role')
    data = request.get_json() or {}
    db = get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Database error'}), 503

    prefs = {
        'urgent_alerts': bool(data.get('urgent_alerts', True)),
        'stock_expiry_alerts': bool(data.get('stock_expiry_alerts', True)),
        'invoice_billing_alerts': bool(data.get('invoice_billing_alerts', True)),
        'email_digest': bool(data.get('email_digest', False))
    }

    if role == 'ADMIN':
        db.users.update_one({'role': 'ADMIN'}, {'$set': {'notification_prefs': prefs, 'updated_at': datetime.now()}})
    elif role == 'COORDINATOR':
        coord_id = user.get('coordinator_id') or user.get('user_id')
        db.coordinators.update_one({'coordinator_id': coord_id}, {'$set': {'notification_prefs': prefs, 'updated_at': datetime.now()}})
    elif role == 'HOSPITAL':
        hosp_id = user.get('hospital_id') or user.get('user_id')
        db.hospitals.update_one({'hospital_id': hosp_id}, {'$set': {'notification_prefs': prefs, 'updated_at': datetime.now()}})

    return jsonify({
        'success': True,
        'message': 'Notification preferences saved successfully!',
        'preferences': prefs
    })
