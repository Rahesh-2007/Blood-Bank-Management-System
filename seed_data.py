from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from database import get_db, init_db, check_db_connection
from config import Config

def seed_all(force=False):
    is_connected, msg = check_db_connection()
    if not is_connected:
        print(f"[ERROR] Cannot seed database: {msg}")
        return False

    db = get_db()
    init_db()

    # Check if already seeded and not force
    if not force and db.hospitals.count_documents({}) > 0:
        print("[INFO] Database already contains records. Skipping seed. (Use force=True to reseed)")
        return True

    print("[INFO] Seeding initial Blood Bank database records...")

    # 1. Reset collections if force
    if force:
        db.users.drop()
        db.coordinators.drop()
        db.hospitals.drop()
        db.donors.drop()
        db.blood_bags.drop()
        db.blood_requests.drop()
        db.invoices.drop()
        db.counters.drop()
        init_db()

    now = datetime.now()

    # 2. Seed Admin User
    db.users.update_one(
        {'email': Config.ADMIN_EMAIL},
        {
            '$set': {
                'email': Config.ADMIN_EMAIL,
                'password': generate_password_hash(Config.ADMIN_PASSWORD),
                'name': Config.ADMIN_NAME,
                'role': 'ADMIN',
                'is_verified': True,
                'created_at': now
            }
        },
        upsert=True
    )

    # 3. Seed Coordinators
    coordinators_data = [
        {
            'coordinator_id': 'COORD101',
            'name': 'Dr. Sarah Jenkins',
            'email': 'coord@bloodbank.org',
            'password': generate_password_hash('coord123'),
            'branch': 'Central Red Cross Blood Bank',
            'phone': '+91 98765 43210',
            'is_verified': True,
            'created_at': now - timedelta(days=60)
        },
        {
            'coordinator_id': 'COORD102',
            'name': 'Mark Peterson',
            'email': 'mark@bloodbank.org',
            'password': generate_password_hash('coord123'),
            'branch': 'Metro South Collection Center',
            'phone': '+91 98765 43211',
            'is_verified': True,
            'created_at': now - timedelta(days=30)
        }
    ]
    for c in coordinators_data:
        db.coordinators.update_one({'email': c['email']}, {'$set': c}, upsert=True)

    # 4. Seed Hospitals
    hospitals_data = [
        {
            'hospital_id': 'HOSP101',
            'name': 'Metro City General Hospital',
            'email': 'metro@hospital.org',
            'password': generate_password_hash('metro123'),
            'phone': '+91 91234 56780',
            'address': 'Plot 42, Health City Avenue, Sector 5',
            'outstanding_balance': 10000.0,
            'is_verified': True,
            'created_at': now - timedelta(days=90),
            'updated_at': now
        },
        {
            'hospital_id': 'HOSP102',
            'name': 'St. Jude Trauma Care & Surgery',
            'email': 'stjude@hospital.org',
            'password': generate_password_hash('stjude123'),
            'phone': '+91 91234 56781',
            'address': '108 Emergency Blvd, West Wing',
            'outstanding_balance': 0.0,
            'is_verified': True,
            'created_at': now - timedelta(days=60),
            'updated_at': now
        },
        {
            'hospital_id': 'HOSP103',
            'name': 'Apex Multi-Speciality Center',
            'email': 'apex@hospital.org',
            'password': generate_password_hash('apex123'),
            'phone': '+91 91234 56782',
            'address': 'Building 7, Medipark Boulevard',
            'outstanding_balance': 5000.0,
            'is_verified': True,
            'created_at': now - timedelta(days=30),
            'updated_at': now
        }
    ]
    for h in hospitals_data:
        db.hospitals.update_one({'hospital_id': h['hospital_id']}, {'$set': h}, upsert=True)

    # 5. Seed Donors (Diverse set for testing eligibility logic)
    donors_data = [
        {
            'donor_id': 'DON1001',
            'name': 'Rahul Sharma',
            'age': 28,
            'gender': 'Male',
            'blood_group': 'O+',
            'contact': '+91 98111 22334',
            'email': 'rahul.s@example.com',
            'weight': 68.0,
            'has_health_issues': False,
            'health_notes': 'None, perfectly healthy regular donor',
            'last_donation_date': (now - timedelta(days=150)).isoformat(),
            'eligible': True,
            'eligibility_reasons': [],
            'total_donations': 3,
            'created_at': now - timedelta(days=150)
        },
        {
            'donor_id': 'DON1002',
            'name': 'Ananya Verma',
            'age': 24,
            'gender': 'Female',
            'blood_group': 'A+',
            'contact': '+91 98222 33445',
            'email': 'ananya.v@example.com',
            'weight': 54.0,
            'has_health_issues': False,
            'health_notes': 'Healthy donor',
            'last_donation_date': (now - timedelta(days=20)).isoformat(),
            'eligible': False,
            'eligibility_reasons': ['Donation interval restriction: Must wait 4 months (120 days) between donations.'],
            'total_donations': 1,
            'created_at': now - timedelta(days=20)
        },
        {
            'donor_id': 'DON1003',
            'name': 'David Miller',
            'age': 35,
            'gender': 'Male',
            'blood_group': 'B+',
            'contact': '+91 98333 44556',
            'email': 'david.m@example.com',
            'weight': 75.0,
            'has_health_issues': False,
            'health_notes': 'Clear',
            'last_donation_date': (now - timedelta(days=180)).isoformat(),
            'eligible': True,
            'eligibility_reasons': [],
            'total_donations': 4,
            'created_at': now - timedelta(days=180)
        },
        {
            'donor_id': 'DON1004',
            'name': 'Priya Nair',
            'age': 17,
            'gender': 'Female',
            'blood_group': 'AB+',
            'contact': '+91 98444 55667',
            'email': 'priya.n@example.com',
            'weight': 42.0,
            'has_health_issues': False,
            'health_notes': 'Underage & underweight sample',
            'last_donation_date': None,
            'eligible': False,
            'eligibility_reasons': ['Age must be between 18 and 60 years.', 'Weight must be at least 45 kg.'],
            'total_donations': 0,
            'created_at': now - timedelta(days=10)
        },
        {
            'donor_id': 'DON1005',
            'name': 'Amitabh Roy',
            'age': 45,
            'gender': 'Male',
            'blood_group': 'O-',
            'contact': '+91 98555 66778',
            'email': 'amitabh.r@example.com',
            'weight': 80.0,
            'has_health_issues': False,
            'health_notes': 'Universal donor',
            'last_donation_date': (now - timedelta(days=130)).isoformat(),
            'eligible': True,
            'eligibility_reasons': [],
            'total_donations': 5,
            'created_at': now - timedelta(days=130)
        },
        {
            'donor_id': 'DON1006',
            'name': 'Simran Kaur',
            'age': 31,
            'gender': 'Female',
            'blood_group': 'A-',
            'contact': '+91 98666 77889',
            'email': 'simran.k@example.com',
            'weight': 58.0,
            'has_health_issues': False,
            'health_notes': 'Eligible donor',
            'last_donation_date': (now - timedelta(days=140)).isoformat(),
            'eligible': True,
            'eligibility_reasons': [],
            'total_donations': 2,
            'created_at': now - timedelta(days=140)
        }
    ]
    for d in donors_data:
        d['is_verified'] = True
        d['password'] = generate_password_hash('donor123')
        db.donors.update_one({'donor_id': d['donor_id']}, {'$set': d}, upsert=True)
        # Also sync to users
        db.users.update_one(
            {'email': d['email']},
            {
                '$set': {
                    'email': d['email'],
                    'name': d['name'],
                    'password': d['password'],
                    'role': 'DONOR',
                    'donor_id': d['donor_id'],
                    'is_verified': True,
                    'created_at': d.get('created_at', now)
                }
            },
            upsert=True
        )

    # 6. Seed Blood Bags (With realistic collection dates, 35-day expiry, varied blood groups for FIFO demonstration)
    bags_seed = [
        # O+ Bags
        ('BAG10001', 'O+', 'DON1001', 'Rahul Sharma', now - timedelta(days=30), now + timedelta(days=5), 'Available', 'Freezer A-1'),
        ('BAG10002', 'O+', 'DON1001', 'Rahul Sharma', now - timedelta(days=20), now + timedelta(days=15), 'Available', 'Freezer A-1'),
        ('BAG10003', 'O+', 'DON1005', 'Amitabh Roy', now - timedelta(days=10), now + timedelta(days=25), 'Available', 'Freezer A-2'),
        ('BAG10004', 'O+', 'DON1001', 'Rahul Sharma', now - timedelta(days=5), now + timedelta(days=30), 'Available', 'Freezer A-2'),
        ('BAG10005', 'O+', 'DON1003', 'David Miller', now - timedelta(days=2), now + timedelta(days=33), 'Available', 'Freezer A-3'),
        ('BAG10006', 'O+', 'DON1005', 'Amitabh Roy', now - timedelta(days=1), now + timedelta(days=34), 'Available', 'Freezer A-3'),
        ('BAG10007', 'O+', 'DON1001', 'Rahul Sharma', now, now + timedelta(days=35), 'Available', 'Freezer A-3'),
        ('BAG10008', 'O+', 'DON1003', 'David Miller', now, now + timedelta(days=35), 'Available', 'Freezer A-3'),
        # A+ Bags
        ('BAG10009', 'A+', 'DON1002', 'Ananya Verma', now - timedelta(days=25), now + timedelta(days=10), 'Available', 'Freezer B-1'),
        ('BAG10010', 'A+', 'DON1002', 'Ananya Verma', now - timedelta(days=15), now + timedelta(days=20), 'Available', 'Freezer B-1'),
        ('BAG10011', 'A+', 'DON1006', 'Simran Kaur', now - timedelta(days=8), now + timedelta(days=27), 'Available', 'Freezer B-2'),
        ('BAG10012', 'A+', 'DON1002', 'Ananya Verma', now - timedelta(days=3), now + timedelta(days=32), 'Available', 'Freezer B-2'),
        ('BAG10013', 'A+', 'DON1006', 'Simran Kaur', now - timedelta(days=1), now + timedelta(days=34), 'Available', 'Freezer B-2'),
        # B+ Bags
        ('BAG10014', 'B+', 'DON1003', 'David Miller', now - timedelta(days=18), now + timedelta(days=17), 'Available', 'Freezer C-1'),
        ('BAG10015', 'B+', 'DON1003', 'David Miller', now - timedelta(days=4), now + timedelta(days=31), 'Available', 'Freezer C-1'),
        # O- Bags
        ('BAG10016', 'O-', 'DON1005', 'Amitabh Roy', now - timedelta(days=12), now + timedelta(days=23), 'Available', 'Freezer D-1'),
        ('BAG10017', 'O-', 'DON1005', 'Amitabh Roy', now - timedelta(days=6), now + timedelta(days=29), 'Available', 'Freezer D-1'),
        ('BAG10018', 'O-', 'DON1005', 'Amitabh Roy', now - timedelta(days=1), now + timedelta(days=34), 'Available', 'Freezer D-1'),
        # A- Bags
        ('BAG10019', 'A-', 'DON1006', 'Simran Kaur', now - timedelta(days=14), now + timedelta(days=21), 'Available', 'Freezer E-1'),
        # AB+ Bags
        ('BAG10020', 'AB+', 'DON1003', 'David Miller', now - timedelta(days=10), now + timedelta(days=25), 'Available', 'Freezer F-1'),
        ('BAG10021', 'AB+', 'DON1001', 'Rahul Sharma', now - timedelta(days=2), now + timedelta(days=33), 'Available', 'Freezer F-1'),
        # (AB- is left with 0 bags to showcase OUT OF STOCK status!)
    ]

    for item in bags_seed:
        bag_id, bg, don_id, don_nm, col_d, exp_d, status, loc = item
        price = Config.BLOOD_PRICES.get(bg, 2500)
        bag_doc = {
            'bag_id': bag_id,
            'blood_group': bg,
            'donor_id': don_id,
            'donor_name': don_nm,
            'collection_date': col_d,
            'expiry_date': exp_d,
            'volume_ml': 450,
            'storage_location': loc,
            'status': status,
            'selling_price': price,
            'collected_by': 'Dr. Sarah Jenkins',
            'issued_to_hospital_id': None,
            'issued_to_hospital_name': None,
            'issued_date': None,
            'request_id': None,
            'created_at': col_d
        }
        db.blood_bags.update_one({'bag_id': bag_id}, {'$set': bag_doc}, upsert=True)

    # Set counters
    db.counters.update_one({'name': 'blood_bag_seq'}, {'$set': {'seq': 10025}}, upsert=True)
    db.counters.update_one({'name': 'donor_seq'}, {'$set': {'seq': 1007}}, upsert=True)
    db.counters.update_one({'name': 'blood_req_seq'}, {'$set': {'seq': 1005}}, upsert=True)
    db.counters.update_one({'name': 'invoice_seq'}, {'$set': {'seq': 1005}}, upsert=True)
    db.counters.update_one({'name': 'hospital_seq'}, {'$set': {'seq': 105}}, upsert=True)
    db.counters.update_one({'name': 'coord_seq'}, {'$set': {'seq': 105}}, upsert=True)

    # 7. Seed Sample Requests (One HIGH pending, One MEDIUM approved with invoice)
    req1 = {
        'request_id': 'REQ1001',
        'hospital_id': 'HOSP101',
        'hospital_name': 'Metro City General Hospital',
        'blood_group': 'O+',
        'quantity': 3,
        'approved_quantity': 3,
        'remaining_quantity': 0,
        'emergency_level': 'HIGH',
        'emergency_hours': 2,
        'required_by_time': (now - timedelta(hours=1)).isoformat(),
        'status': 'Approved',
        'issued_bag_ids': ['BAG10001', 'BAG10002', 'BAG10003'],
        'notes': 'Emergency ICU trauma operation unit',
        'admin_remarks': 'Approved immediately under HIGH priority.',
        'invoice_id': 'INV1001',
        'created_at': now - timedelta(hours=3),
        'updated_at': now - timedelta(hours=2)
    }
    db.blood_requests.update_one({'request_id': req1['request_id']}, {'$set': req1}, upsert=True)

    # Sample Invoice for REQ1001
    inv1 = {
        'invoice_number': 'INV1001',
        'request_id': 'REQ1001',
        'hospital_id': 'HOSP101',
        'hospital_name': 'Metro City General Hospital',
        'blood_group': 'O+',
        'quantity': 3,
        'blood_bags': ['BAG10001', 'BAG10002', 'BAG10003'],
        'unit_price': 2800,
        'subtotal': 8400.0,
        'tax_rate_percent': 5,
        'tax_amount': 420.0,
        'total_amount': 8820.0,
        'status': 'PENDING',
        'invoice_date': now - timedelta(hours=2),
        'paid_date': None,
        'payment_reference': None,
        'created_at': now - timedelta(hours=2)
    }
    db.invoices.update_one({'invoice_number': inv1['invoice_number']}, {'$set': inv1}, upsert=True)

    # Seed an active pending HIGH priority request for demonstration in Admin Dashboard
    req2 = {
        'request_id': 'REQ1002',
        'hospital_id': 'HOSP102',
        'hospital_name': 'St. Jude Trauma Care & Surgery',
        'blood_group': 'A+',
        'quantity': 2,
        'approved_quantity': 0,
        'remaining_quantity': 2,
        'emergency_level': 'HIGH',
        'emergency_hours': 2,
        'required_by_time': (now + timedelta(hours=1, minutes=45)).isoformat(),
        'status': 'Pending',
        'issued_bag_ids': [],
        'notes': 'Urgent cardiac surgery support needed',
        'admin_remarks': None,
        'invoice_id': None,
        'created_at': now - timedelta(minutes=15),
        'updated_at': now - timedelta(minutes=15)
    }
    db.blood_requests.update_one({'request_id': req2['request_id']}, {'$set': req2}, upsert=True)

    print("[SUCCESS] Initial data seed completed successfully!")
    return True

if __name__ == '__main__':
    seed_all(force=True)
