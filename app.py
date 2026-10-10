import os
from flask import Flask, render_template, jsonify, session, redirect, url_for
from config import Config
from database import init_db, check_db_connection

# Import route blueprints
from routes.auth_routes import auth_bp
from routes.donor_routes import donor_bp
from routes.donation_routes import donation_bp
from routes.stock_routes import stock_bp
from routes.request_routes import request_bp
from routes.invoice_routes import invoice_bp
from routes.hospital_routes import hospital_bp
from routes.staff_routes import staff_bp
from routes.coordinator_routes import coordinator_bp
from routes.report_routes import report_bp

app = Flask(__name__)
app.config.from_object(Config)

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(donor_bp)
app.register_blueprint(donation_bp)
app.register_blueprint(stock_bp)
app.register_blueprint(request_bp)
app.register_blueprint(invoice_bp)
app.register_blueprint(hospital_bp)
app.register_blueprint(staff_bp)
app.register_blueprint(coordinator_bp)
app.register_blueprint(report_bp)

# Page Routes
@app.route('/')
@app.route('/login')
def index_page():
    return render_template('index.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

@app.route('/staff')
@app.route('/coordinator')
def coordinator_page():
    return render_template('staff.html')

@app.route('/hospital')
def hospital_page():
    return render_template('hospital.html')

@app.route('/api/system/status', methods=['GET'])
def system_status():
    is_connected, msg = check_db_connection()
    return jsonify({
        'status': 'ONLINE' if is_connected else 'DB_DISCONNECTED',
        'mongodb_connected': is_connected,
        'message': 'Database is connected and healthy.' if is_connected else 'Database connection error'
    })

# Auto-initialize database on application launch if reachable
with app.app_context():
    is_conn, msg = check_db_connection()
    if is_conn:
        init_db()
        # Automatically run seed if empty
        from seed_data import seed_all
        seed_all(force=False)
        print(f"[SUCCESS] Connected to MongoDB ({Config.DB_NAME}) & Initialized successfully.")
    else:
        print(f"[WARN] MongoDB not reachable at startup: {msg}")
        print("[TIP] Open MongoDB Compass or start the MongoDB service, then refresh or run 'python seed_data.py'.")

if __name__ == '__main__':
    print(f"================================================================")
    print(f"[BLOOD BANK] Management System running on http://127.0.0.1:{Config.PORT}")
    print(f"MongoDB Target: {Config.MONGO_URI} [Database: {Config.DB_NAME}]")
    print(f"================================================================")
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)
