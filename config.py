import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-blood-bank-dev')
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://127.0.0.1:27017/')
    DB_NAME = os.getenv('DB_NAME', 'blood_bank_db')
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('FLASK_ENV', 'development') == 'development'

    # Admin Credentials
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@bloodbank.org')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
    ADMIN_NAME = os.getenv('ADMIN_NAME', 'Super Admin')

    # Predefined Pricing per Blood Group (INR)
    BLOOD_PRICES = {
        'A+': 2500,
        'A-': 3000,
        'B+': 2500,
        'B-': 3000,
        'AB+': 3500,
        'AB-': 4000,
        'O+': 2800,
        'O-': 3500
    }

    # Emergency Level Duration in Hours
    EMERGENCY_HOURS = {
        'HIGH': 2,
        'MEDIUM': 4,
        'LOW': 8
    }

    # Tax Rate (5%)
    TAX_RATE = 0.05

    # Shelf Life of Blood Bag in Days
    BLOOD_SHELF_LIFE_DAYS = 35

    # Minimum Donation Interval in Days (4 Months ≈ 120 Days)
    MIN_DONATION_INTERVAL_DAYS = 120

    # Eligibility Age & Weight criteria
    MIN_DONOR_AGE = 18
    MAX_DONOR_AGE = 60
    MIN_DONOR_WEIGHT = 45  # kg
