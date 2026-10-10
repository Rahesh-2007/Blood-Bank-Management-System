from datetime import datetime, date
from bson import ObjectId
from pymongo import MongoClient, ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import Config
import certifi

_client = None
_db = None

def get_client():
    global _client
    if _client is None:
        try:
            client_kwargs = {
                "serverSelectionTimeoutMS": 10000,
                "connectTimeoutMS": 10000,
                "socketTimeoutMS": 30000,
                "retryWrites": True
            }
            # For cloud mongodb+srv URIs, use certifi CA bundle for reliable TLS validation
            if "mongodb+srv://" in Config.MONGO_URI or "ssl=true" in Config.MONGO_URI.lower():
                client_kwargs["tlsCAFile"] = certifi.where()

            _client = MongoClient(
                Config.MONGO_URI,
                **client_kwargs
            )
        except Exception as e:
            print(f"[ERROR] Failed to initialize MongoClient: {e}")
            _client = None
    return _client

def get_db():
    global _db, _client
    if _db is None:
        client = get_client()
        if client:
            try:
                _db = client[Config.DB_NAME]
            except Exception as e:
                print(f"[ERROR] Failed to obtain database handle: {e}")
                _db = None
    return _db

def check_db_connection():
    """Verify if MongoDB is reachable and return status dict."""
    global _client, _db
    try:
        client = get_client()
        if client is None:
            # Retry initialization once
            _client = None
            _db = None
            client = get_client()
            if client is None:
                return False, "MongoClient not initialized"
        # Run a quick ping command
        client.admin.command('ping')
        return True, "Connected successfully to MongoDB"
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        # Reset cached client on network failure so subsequent calls can retry
        _client = None
        _db = None
        return False, f"Could not connect to MongoDB. Error: {e}"
    except Exception as e:
        _client = None
        _db = None
        return False, str(e)

def init_db():
    """Create indexes and initialize atomic sequence counters."""
    db = get_db()
    if db is None:
        return False
    try:
        # Counters for sequence generation
        db.counters.create_index("name", unique=True)
        
        # Pre-seed initial sequence counters atomically if they don't exist yet
        initial_counters = [
            ("blood_bag_seq", 10000),
            ("donor_seq", 1000),
            ("blood_req_seq", 1000),
            ("invoice_seq", 1000),
            ("hospital_seq", 100),
            ("coord_seq", 100),
            ("payment_seq", 1000),
            ("activity_seq", 1000)
        ]
        for name, initial_seq in initial_counters:
            db.counters.update_one(
                {"name": name},
                {"$setOnInsert": {"name": name, "seq": initial_seq}},
                upsert=True
            )

        # Donors
        db.donors.create_index("donor_id", unique=True)
        db.donors.create_index("email", sparse=True)
        db.donors.create_index("blood_group")
        db.donors.create_index("status")

        # Blood Bags
        db.blood_bags.create_index("bag_id", unique=True)
        db.blood_bags.create_index([("blood_group", ASCENDING), ("status", ASCENDING), ("expiry_date", ASCENDING)])
        db.blood_bags.create_index("status")
        db.blood_bags.create_index("donor_id")

        # Hospitals
        db.hospitals.create_index("hospital_id", unique=True)
        db.hospitals.create_index("email", unique=True)

        # Coordinators
        db.coordinators.create_index("coordinator_id", unique=True)
        db.coordinators.create_index("email", unique=True)

        # Blood Requests
        db.blood_requests.create_index("request_id", unique=True)
        db.blood_requests.create_index([("status", ASCENDING), ("emergency_level", ASCENDING)])
        db.blood_requests.create_index("hospital_id")

        # Invoices
        db.invoices.create_index("invoice_number", unique=True)
        db.invoices.create_index("hospital_id")
        db.invoices.create_index("request_id")

        # Payments
        db.payments.create_index("payment_id", unique=True)
        db.payments.create_index("invoice_number")
        db.payments.create_index("hospital_id")

        # Activity Logs
        db.activity_logs.create_index([("timestamp", DESCENDING)])
        db.activity_logs.create_index("actor_id")

        return True
    except Exception as e:
        print(f"[WARN] Index initialization notice: {e}")
        return False

def get_next_sequence(name, prefix="SEQ", start_val=10001):
    """
    Generate sequential IDs such as BAG10001, REQ10001, INV10001.
    Uses an atomic find_one_and_update on the 'counters' collection.
    """
    db = get_db()
    if db is None:
        raise RuntimeError("Database connection not established")
    
    # Atomically increment counter
    counter = db.counters.find_one_and_update(
        {"name": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    
    seq_val = counter.get("seq", start_val)
    if seq_val < start_val:
        # One-time alignment if needed
        aligned = db.counters.find_one_and_update(
            {"name": name, "seq": {"$lt": start_val}},
            {"$set": {"seq": start_val}},
            return_document=ReturnDocument.AFTER
        )
        if aligned:
            seq_val = aligned.get("seq", start_val)

    return f"{prefix}{seq_val}"

def serialize_doc(doc):
    """Recursively convert MongoDB document (ObjectId, datetimes) to JSON-serializable dict."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        result = {}
        for k, v in doc.items():
            if k == '_id':
                result['id'] = str(v)
            elif isinstance(v, ObjectId):
                result[k] = str(v)
            elif isinstance(v, (datetime, date)):
                result[k] = v.isoformat()
            elif isinstance(v, dict):
                result[k] = serialize_doc(v)
            elif isinstance(v, list):
                result[k] = serialize_doc(v)
            else:
                result[k] = v
        return result
    return doc
