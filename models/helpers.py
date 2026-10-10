import re
from functools import wraps
from datetime import datetime, timedelta, date
from flask import session, jsonify, request
from config import Config

BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']

def get_session_user():
    """Retrieve authenticated user dict from Flask session."""
    return session.get('user')

def login_required(f):
    """Decorator to enforce that the user is authenticated in the session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_session_user()
        if not user or not user.get('role'):
            return jsonify({
                'success': False,
                'message': 'Authentication required. Please sign in to continue.',
                'authenticated': False
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    """Decorator to enforce specific user roles (e.g. ['ADMIN'], ['COORDINATOR', 'ADMIN'])."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_session_user()
            if not user or not user.get('role'):
                return jsonify({
                    'success': False,
                    'message': 'Authentication required. Please sign in to continue.',
                    'authenticated': False
                }), 401
            
            user_role = user.get('role', '').upper()
            normalized_roles = [r.upper() for r in allowed_roles]
            
            if user_role not in normalized_roles:
                return jsonify({
                    'success': False,
                    'message': f'Access denied. Required role: {", ".join(allowed_roles)}. Your role: {user_role}.',
                    'authorized': False
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def sanitize_account_doc(doc):
    """Remove password hashes, salt, and sensitive internal credentials before serializing."""
    if not doc or not isinstance(doc, dict):
        return doc
    clean = dict(doc)
    clean.pop('password', None)
    clean.pop('password_hash', None)
    clean.pop('salt', None)
    return clean

def validate_date_string(date_str, field_name="Date"):
    """
    Validate and parse a date string (YYYY-MM-DD or ISO).
    Returns (True, parsed_datetime) or (False, error_message).
    """
    if not date_str:
        return True, None
    if isinstance(date_str, (datetime, date)):
        return True, date_str if isinstance(date_str, datetime) else datetime.combine(date_str, datetime.min.time())
    
    date_str_clean = str(date_str).strip().replace("Z", "")
    for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f'):
        try:
            parsed = datetime.strptime(date_str_clean, fmt)
            return True, parsed
        except ValueError:
            continue
            
    return False, f"Invalid {field_name} format. Expected YYYY-MM-DD (Received: '{date_str}')."

def check_donor_eligibility(age, weight, has_health_issues=False, last_donation_date=None, is_active=True):
    """
    Evaluates donor eligibility according to clinical blood bank rules:
    - Active status (not deactivated)
    - Age >= 18 AND Age <= 60
    - Weight >= 45 kg
    - No active health issues or contraindications
    - 4-month (120-day) interval between donations
    Returns: (is_eligible, reasons_list, next_eligible_date_iso)
    """
    reasons = []
    next_eligible_dt = None

    if not is_active:
        reasons.append("Donor account is currently deactivated / on clinical hold.")

    try:
        age_int = int(age)
        if age_int < Config.MIN_DONOR_AGE or age_int > Config.MAX_DONOR_AGE:
            reasons.append(f"Age must be between {Config.MIN_DONOR_AGE} and {Config.MAX_DONOR_AGE} years (Provided: {age_int}).")
    except (ValueError, TypeError):
        return False, ["Invalid age value."], None

    try:
        weight_flt = float(weight)
        if weight_flt < Config.MIN_DONOR_WEIGHT:
            reasons.append(f"Weight must be at least {Config.MIN_DONOR_WEIGHT} kg for safe blood donation (Provided: {weight_flt} kg).")
    except (ValueError, TypeError):
        return False, ["Invalid weight value."], None

    if bool(has_health_issues):
        reasons.append("Donor reports active health condition or medication contraindication.")

    if last_donation_date:
        valid, last_dt = validate_date_string(last_donation_date, "Last Donation Date")
        if not valid:
            reasons.append(last_dt)
        elif last_dt:
            next_eligible_dt = last_dt + timedelta(days=Config.MIN_DONATION_INTERVAL_DAYS)
            now = datetime.now()
            days_passed = (now - last_dt).days
            if days_passed < Config.MIN_DONATION_INTERVAL_DAYS:
                days_left = Config.MIN_DONATION_INTERVAL_DAYS - days_passed
                reasons.append(f"Donation interval constraint: 4 months (120 days) required between donations. {days_left} day(s) remaining (Next eligible: {next_eligible_dt.strftime('%d-%b-%Y')}).")

    is_eligible = (len(reasons) == 0)
    next_eligible_str = next_eligible_dt.strftime('%Y-%m-%d') if next_eligible_dt else None
    return is_eligible, reasons, next_eligible_str

def calculate_urgency_timeline(emergency_level, created_at=None, request_status="Pending"):
    """
    Calculate required deadline and live countdown.
    Overdue is only applied if the request is still awaiting fulfilment (Pending or Partially Approved).
    """
    level = str(emergency_level).upper() if emergency_level else 'MEDIUM'
    duration_hours = Config.EMERGENCY_HOURS.get(level, 4)
    
    if created_at is None:
        created_at = datetime.now()
    elif isinstance(created_at, str):
        valid, parsed_dt = validate_date_string(created_at, "Created Date")
        created_at = parsed_dt if valid and parsed_dt else datetime.now()

    required_by = created_at + timedelta(hours=duration_hours)
    now = datetime.now()
    seconds_remaining = int((required_by - now).total_seconds())
    
    # Overdue flag applies ONLY if request is active / awaiting fulfilment
    is_awaiting_fulfilment = request_status in ['Pending', 'Partially Approved']
    is_overdue = (seconds_remaining <= 0) and is_awaiting_fulfilment

    return {
        "emergency_level": level,
        "duration_hours": duration_hours,
        "created_at": created_at.isoformat(),
        "required_by": required_by.isoformat(),
        "seconds_remaining": max(0, seconds_remaining) if not is_overdue else seconds_remaining,
        "is_overdue": is_overdue,
        "is_awaiting_fulfilment": is_awaiting_fulfilment
    }

def log_activity(db, actor_id, actor_name, actor_role, action, description, target_type=None, target_id=None, metadata=None):
    """
    Record an immutable audit log entry in the activity_logs collection.
    """
    if db is None:
        return
    try:
        from database import get_next_sequence
        log_id = get_next_sequence('activity_seq', prefix='ACT', start_val=1001)
        doc = {
            'log_id': log_id,
            'actor_id': actor_id or 'SYSTEM',
            'actor_name': actor_name or 'System Automated',
            'actor_role': actor_role or 'SYSTEM',
            'action': action,
            'description': description,
            'target_type': target_type,
            'target_id': target_id,
            'metadata': metadata or {},
            'timestamp': datetime.now()
        }
        db.activity_logs.insert_one(doc)
    except Exception as e:
        print(f"[WARN] Failed to write activity log: {e}")
