# 🩸 Blood Bank Management System (Flask + MongoDB)

An enterprise-grade, end-to-end **Blood Bank Management System** built with **Flask**, **Python**, **MongoDB (Compass / Atlas)**, and a modern responsive interface.

---

## 🏗️ Project Architecture & Folder Structure

```
End-Sem-Project/
│
├── app.py                     # Main Flask Application Entry Point & Page Routes
├── config.py                  # App Configuration, Blood Prices, Urgency & Tax Settings
├── database.py                # MongoDB Connection, Counters, Sequence Generators & Indexes
├── seed_data.py               # Initial Data Seeder (Admin, Coordinators, Hospitals, Bags, Donors)
├── requirements.txt           # Python Dependencies (Flask, pymongo, python-dotenv, etc.)
├── .env                       # Active Environment Configuration
├── .env.example               # Example Environment Template
│
├── models/
│   ├── __init__.py
│   └── helpers.py             # Business Logic (Eligibility Checker, FIFO Sorter, Urgency Calculator)
│
├── routes/                    # Modular Blueprints (Controllers)
│   ├── __init__.py
│   ├── auth_routes.py         # Login/Logout for Admin, Coordinator, Hospital
│   ├── donor_routes.py        # Donor Registration & Live Eligibility Evaluation
│   ├── donation_routes.py     # Blood Collection & Bag Generation (BAG10001...)
│   ├── stock_routes.py        # Live Stock Calculations & Categorization (GOOD/LOW/CRITICAL/OUT)
│   ├── request_routes.py      # Hospital Blood Requests & Admin FIFO Approvals
│   ├── invoice_routes.py      # 5% Tax Invoice Generation & Hospital Payment Reconciliation
│   ├── hospital_routes.py     # Hospital Entity Management & Balance Tracking
│   ├── coordinator_routes.py  # Coordinator Management
│   └── report_routes.py       # Global Analytics, CSV Exports & Text Audit Reports
│
├── static/
│   ├── css/
│   │   ├── style.css          # Design System, Glassmorphism, Responsive Sidebar, Print Invoices
│   │   └── toast.css          # Floating Toast Notifications
│   └── js/
│       ├── api.js             # Common API Fetch Client & Formatters
│       ├── auth.js            # Multi-Role Login Switcher & Auto-Fill Demo Helper
│       ├── admin.js           # Super Admin Console (FIFO Allocation, Urgency View, Reports)
│       ├── coordinator.js     # Coordinator Console (Live Eligibility, Donation Recorder)
│       └── hospital.js        # Hospital Portal (Request Submissions, Invoices, Payment Modal)
│
└── templates/
    ├── index.html             # Multi-Role Landing & Login Page
    ├── admin.html             # Super Admin Dashboard
    ├── coordinator.html       # Blood Bank Coordinator Portal
    └── hospital.html          # Hospital Portal & Billing Ledger
```

---

## 🧭 How to Connect MongoDB Compass to This Project

You can connect either via **Local MongoDB Community Server** or free **MongoDB Atlas Cloud**.

### Option A: Local MongoDB Compass (Recommended for Local Dev)
1. **Start MongoDB**: Ensure MongoDB is running locally on your computer (default port `27017`).
2. **Open MongoDB Compass**:
   - In the **New Connection** screen, use connection string:
     ```text
     mongodb://127.0.0.1:27017/
     ```
   - Click **Connect**.
3. **Verify `.env`**:
   Ensure your `.env` file in the project folder contains:
   ```env
   MONGO_URI=mongodb://127.0.0.1:27017/
   DB_NAME=blood_bank_db
   ```
4. **Seed Database**:
   Run in your terminal:
   ```bash
   python seed_data.py
   ```
5. **Inspect in Compass**:
   In MongoDB Compass, refresh the left sidebar. You will see the `blood_bank_db` database with collections:
   - `users`
   - `coordinators`
   - `hospitals`
   - `donors`
   - `blood_bags`
   - `blood_requests`
   - `invoices`
   - `counters`

---

### Option B: MongoDB Atlas Cloud Free Tier
1. Open [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) and create a free M0 cluster.
2. Click **Connect** → **Compass** → Copy the connection string (e.g. `mongodb+srv://<username>:<password>@cluster0.mongodb.net/`).
3. Paste the connection string into MongoDB Compass and into your `.env` file:
   ```env
   MONGO_URI=mongodb+srv://your_user:your_password@cluster0.mongodb.net/
   DB_NAME=blood_bank_db
   ```
4. Run `python seed_data.py` to seed data into your cloud cluster.

---

## 🚀 How to Run the Project

1. **Install Dependencies**:
   ```bash
   python -m pip install -r requirements.txt
   ```

2. **Seed Initial Demo Data**:
   ```bash
   python seed_data.py
   ```

3. **Start the Flask Server**:
   ```bash
   python app.py
   ```

4. **Open Browser**:
   Navigate to:
   ```text
   http://127.0.0.1:5000
   ```

---

## 🔐 Pre-Configured Demo Credentials

| Role | Identifier / Email | Password | Details |
|---|---|---|---|
| 👨💼 **Super Admin** | `admin@bloodbank.org` | `admin123` | Global control, request processing, reports |
| 👨⚕️ **Coordinator** | `coord@bloodbank.org` | `coord123` | Donor registration, donation & bag logging |
| 🏥 **Hospital** | ID: `HOSP101`<br>Email: `metro@hospital.org` | `metro123` | Blood request creation, invoice payment |

> 💡 *Note: The login page includes **Auto Fill** buttons for one-click demo testing!*

---

## 🩸 Core Business Logic Implementation Highlights

1. **Strict Donor Eligibility**:
   - Age between **18 and 60 years**
   - Weight **≥ 45 kg**
   - No active health issues
   - **4-month (120 days)** mandatory interval between donations
2. **Blood Bag Generation**:
   - Unique ID sequence: `BAG10001`, `BAG10002`...
   - **35-day shelf life** (`expiry_date = collection_date + 35 days`)
   - Donor marked ineligible for 4 months post-donation.
3. **Usable Stock & Categorization**:
   - Usable stock counts only bags with `Status == 'Available'` and `Expiry Date >= Today`.
   - Categories: `0` = OUT OF STOCK, `1–2` = CRITICAL, `3–4` = LOW, `5+` = GOOD.
4. **Emergency Priority Windows**:
   - 🔴 **HIGH**: 2 hours
   - 🟠 **MEDIUM**: 4 hours
   - 🟢 **LOW**: 8 hours
5. **Earliest-Expiry-First (FIFO) Issuance**:
   - Admin approval selects earliest expiring available units first to prevent spoilage.
6. **Partial Approval vs Full Approval vs Rejection**:
   - Partial approval issues available units, remaining units stay pending.
7. **Invoice & Tax Calculation**:
   - Triggered automatically upon Full Approval.
   - Applies **5% GST / Tax**: `Subtotal + 5% = Total Amount`.
   - Adds total amount to hospital's outstanding balance.
8. **Hospital Invoice Payment**:
   - Verifies `Payment Amount >= Invoice Total`.
   - Marks invoice as `PAID` and decrements hospital balance.
9. **Data Export & Reporting**:
   - Full CSV downloads for bags, requests, invoices, donors, and hospitals.
   - Printable invoices and formatted Text Audit Reports.
