import os
from PIL import Image, ImageDraw, ImageFont

os.makedirs('report_assets', exist_ok=True)

def get_font(size, bold=False):
    try:
        font_name = 'segoeuib.ttf' if bold else 'segoeui.ttf'
        return ImageFont.truetype(font_name, size)
    except:
        try:
            font_name = 'arialbd.ttf' if bold else 'arial.ttf'
            return ImageFont.truetype(font_name, size)
        except:
            return ImageFont.load_default()

def draw_header(draw, w, title, subtitle=''):
    draw.rectangle([0, 0, w, 50], fill='#881337')
    draw.text((20, 12), title, fill='#ffffff', font=get_font(18, True))
    if subtitle:
        draw.text((w - 280, 16), subtitle, fill='#fecdd3', font=get_font(12, False))

# FIG 3.1: Landing & Auth
def make_fig_3_1():
    w, h = 950, 520
    img = Image.new('RGB', (w, h), color='#0f172a')
    draw = ImageDraw.Draw(img)
    draw_header(draw, w, 'Blood Bank Management System', 'Secure Multi-Role Portal')
    
    # Left Hero Section
    draw.rectangle([30, 75, 480, 480], fill='#1e293b', outline='#334155', width=1)
    draw.text((50, 100), 'Centralized Blood Inventory\n& Emergency Logistics System', fill='#ffffff', font=get_font(20, True))
    draw.text((50, 160), '- Automated FIFO Earliest-Expiry-First allocation\n- Strict 4-Month & Medical donor eligibility engine\n- 35-Day blood shelf life automatic calculation\n- Real-time stock alerts (Good, Low, Critical, Out)\n- Direct hospital emergency requests with SLA windows\n- Automated 5% GST invoicing & digital payments', fill='#cbd5e1', font=get_font(13))
    
    # Quick Stats Pills
    draw.rectangle([50, 340, 240, 410], fill='#334155', outline='#475569')
    draw.text((65, 350), 'Usable Stock Units', fill='#94a3b8', font=get_font(11))
    draw.text((65, 370), '148 Units (Live)', fill='#34d399', font=get_font(16, True))
    
    draw.rectangle([260, 340, 450, 410], fill='#334155', outline='#475569')
    draw.text((275, 350), 'Connected Hospitals', fill='#94a3b8', font=get_font(11))
    draw.text((275, 370), '12 Registered', fill='#38bdf8', font=get_font(16, True))
    
    # Right Login Box
    draw.rectangle([510, 75, 920, 480], fill='#1e293b', outline='#e11d48', width=2)
    draw.text((540, 95), 'Account Sign-In', fill='#ffffff', font=get_font(18, True))
    
    # Role Selector Tabs
    draw.rectangle([540, 130, 645, 165], fill='#e11d48')
    draw.text((555, 140), 'Super Admin', fill='#ffffff', font=get_font(12, True))
    draw.rectangle([655, 130, 770, 165], fill='#334155')
    draw.text((668, 140), 'Coordinator', fill='#cbd5e1', font=get_font(12))
    draw.rectangle([780, 130, 890, 165], fill='#334155')
    draw.text((802, 140), 'Hospital', fill='#cbd5e1', font=get_font(12))
    
    # Form Fields
    draw.text((540, 185), 'Email / Hospital ID', fill='#94a3b8', font=get_font(12))
    draw.rectangle([540, 205, 890, 245], fill='#0f172a', outline='#475569')
    draw.text((555, 218), 'admin@bloodbank.org', fill='#ffffff', font=get_font(13))
    
    draw.text((540, 260), 'Password', fill='#94a3b8', font=get_font(12))
    draw.rectangle([540, 280, 890, 320], fill='#0f172a', outline='#475569')
    draw.text((555, 295), '**************', fill='#ffffff', font=get_font(14))
    
    # Login Button
    draw.rectangle([540, 340, 890, 385], fill='#e11d48')
    draw.text((670, 353), 'Sign In to Dashboard', fill='#ffffff', font=get_font(14, True))
    
    # Autofill Demo Badges
    draw.text((540, 410), 'One-Click Demo Auto-Fill:', fill='#94a3b8', font=get_font(11))
    draw.rectangle([540, 430, 640, 460], fill='#334155')
    draw.text((552, 438), 'Admin Demo', fill='#f43f5e', font=get_font(11, True))
    draw.rectangle([650, 430, 765, 460], fill='#334155')
    draw.text((662, 438), 'Coord Demo', fill='#38bdf8', font=get_font(11, True))
    draw.rectangle([775, 430, 890, 460], fill='#334155')
    draw.text((788, 438), 'Hospital Demo', fill='#34d399', font=get_font(11, True))
    
    img.save('report_assets/fig_3_1_landing.png')
    print('Generated fig_3_1_landing.png')

# FIG 3.2: Admin Dashboard
def make_fig_3_2():
    w, h = 950, 520
    img = Image.new('RGB', (w, h), color='#0f172a')
    draw = ImageDraw.Draw(img)
    draw_header(draw, w, 'Blood Bank Management System - Super Admin Console', 'User: admin@bloodbank.org')
    
    # 4 Stat Cards
    cards = [
        ('TOTAL BLOOD BAGS', '215 Bags', '+12 today', '#3b82f6', 30),
        ('USABLE STOCK (AVAILABLE)', '148 Units', 'Valid & Non-Expired', '#10b981', 255),
        ('PENDING REQUESTS', '4 Critical', 'Requires FIFO Action', '#f59e0b', 480),
        ('REVENUE (COLLECTED)', 'Rs. 2,84,500', '5% GST Included', '#ec4899', 705)
    ]
    for title, val, sub, col, x in cards:
        draw.rectangle([x, 70, x + 215, 150], fill='#1e293b', outline=col, width=2)
        draw.text((x + 15, 80), title, fill='#94a3b8', font=get_font(10, True))
        draw.text((x + 15, 100), val, fill='#ffffff', font=get_font(18, True))
        draw.text((x + 15, 128), sub, fill=col, font=get_font(11))
    
    # Urgent Requests Section
    draw.rectangle([30, 170, 920, 330], fill='#1e293b', outline='#334155')
    draw.text((45, 185), 'Active Hospital Emergency Requests (Prioritized by Urgency SLA)', fill='#ffffff', font=get_font(14, True))
    
    # Table Header
    draw.rectangle([45, 215, 905, 245], fill='#334155')
    headers = [('REQ ID', 60), ('HOSPITAL', 140), ('BLOOD GROUP', 310), ('UNITS', 440), ('URGENCY / SLA', 530), ('STATUS', 680), ('ACTION', 800)]
    for h_txt, h_x in headers:
        draw.text((h_x, 222), h_txt, fill='#cbd5e1', font=get_font(11, True))
    
    # Rows
    rows = [
        ('REQ-1042', 'Apollo Speciality Hosp', 'O+ (Positive)', '6 Bags', 'HIGH (2 hr SLA)', 'PENDING', '#ef4444', 255),
        ('REQ-1041', 'City Care Hospital', 'A+ (Positive)', '4 Bags', 'HIGH (2 hr SLA)', 'PARTIAL (2/4)', '#f59e0b', 285)
    ]
    for r_id, hosp, bg, units, urg, st, st_col, y in rows:
        draw.text((60, y), r_id, fill='#38bdf8', font=get_font(11, True))
        draw.text((140, y), hosp, fill='#ffffff', font=get_font(11))
        draw.text((310, y), bg, fill='#f43f5e', font=get_font(11, True))
        draw.text((440, y), units, fill='#ffffff', font=get_font(11))
        draw.rectangle([530, y - 2, 650, y + 18], fill='#7f1d1d')
        draw.text((540, y), urg, fill='#fecdd3', font=get_font(10, True))
        draw.rectangle([680, y - 2, 770, y + 18], fill='#334155')
        draw.text((690, y), st, fill=st_col, font=get_font(10, True))
        draw.rectangle([800, y - 3, 890, y + 19], fill='#e11d48')
        draw.text((812, y), 'FIFO Approve', fill='#ffffff', font=get_font(10, True))
    
    # Analytics / Stock preview
    draw.rectangle([30, 350, 920, 500], fill='#1e293b', outline='#334155')
    draw.text((45, 365), 'Quick Operations & Audit Log Overview', fill='#ffffff', font=get_font(14, True))
    draw.text((45, 395), '- Last FIFO Allocation: 6 units O+ assigned to Apollo Speciality (BAG10012, BAG10015, BAG10018...)\n- Automatic 5% GST Invoice INV-8821 generated for Apollo Hospital (Total: Rs. 8,820)\n- Stock Alert: Blood Group AB- is currently in CRITICAL status (2 units remaining)\n- Donor Registry: 14 new donors screened by Coordinator coord@bloodbank.org today', fill='#94a3b8', font=get_font(12))
    
    img.save('report_assets/fig_3_2_admin_dashboard.png')
    print('Generated fig_3_2_admin_dashboard.png')

# FIG 3.3: Stock Inventory Matrix
def make_fig_3_3():
    w, h = 950, 520
    img = Image.new('RGB', (w, h), color='#0f172a')
    draw = ImageDraw.Draw(img)
    draw_header(draw, w, 'Blood Stock Inventory & Usability Matrix', 'Live Status Categorization')
    
    draw.text((30, 70), 'Live Blood Stock Matrix (Categorized: 5+ GOOD | 3-4 LOW | 1-2 CRITICAL | 0 OUT)', fill='#ffffff', font=get_font(15, True))
    
    groups = [
        ('A+', '28 Bags', 'GOOD (5+)', '#10b981', 'Rs. 1,200', 30, 100),
        ('A-', '6 Bags', 'GOOD (5+)', '#10b981', 'Rs. 1,500', 255, 100),
        ('B+', '34 Bags', 'GOOD (5+)', '#10b981', 'Rs. 1,200', 480, 100),
        ('B-', '4 Bags', 'LOW (3-4)', '#f59e0b', 'Rs. 1,500', 705, 100),
        ('O+', '42 Bags', 'GOOD (5+)', '#10b981', 'Rs. 1,400', 30, 210),
        ('O-', '2 Bags', 'CRITICAL (1-2)', '#ef4444', 'Rs. 2,000', 255, 210),
        ('AB+', '18 Bags', 'GOOD (5+)', '#10b981', 'Rs. 1,300', 480, 210),
        ('AB-', '0 Bags', 'OUT OF STOCK', '#64748b', 'Rs. 1,800', 705, 210)
    ]
    for bg, count, status, col, price, x, y in groups:
        draw.rectangle([x, y, x + 215, y + 95], fill='#1e293b', outline=col, width=2)
        draw.text((x + 15, y + 10), f'Group {bg}', fill='#ffffff', font=get_font(16, True))
        draw.text((x + 120, y + 12), price, fill='#94a3b8', font=get_font(11))
        draw.text((x + 15, y + 38), count, fill='#38bdf8', font=get_font(16, True))
        draw.rectangle([x + 15, y + 68, x + 195, y + 88], fill=col)
        draw.text((x + 30, y + 70), status, fill='#ffffff', font=get_font(10, True))
    
    # Blood Bag Inspection Table
    draw.rectangle([30, 320, 920, 500], fill='#1e293b', outline='#334155')
    draw.text((45, 335), 'Recently Collected Blood Bags & Shelf Life Tracking (35-Day Window)', fill='#ffffff', font=get_font(13, True))
    
    draw.rectangle([45, 360, 905, 385], fill='#334155')
    headers = [('BAG ID', 60), ('BLOOD GROUP', 170), ('COLLECTION DATE', 290), ('EXPIRY DATE', 430), ('DAYS LEFT', 580), ('STATUS', 710), ('DONOR', 820)]
    for h_txt, h_x in headers:
        draw.text((h_x, 366), h_txt, fill='#cbd5e1', font=get_font(10, True))
    
    bags = [
        ('BAG10045', 'O+ (Positive)', '2025-10-05', '2025-11-09', '31 Days left', 'AVAILABLE', '#10b981', 'DNR-5012', 395),
        ('BAG10044', 'A+ (Positive)', '2025-10-04', '2025-11-08', '30 Days left', 'AVAILABLE', '#10b981', 'DNR-5009', 425),
        ('BAG10043', 'B- (Negative)', '2025-09-12', '2025-10-17', '8 Days left (Expiring Soon)', 'AVAILABLE', '#f59e0b', 'DNR-4998', 455)
    ]
    for bid, bg, cd, ed, dl, st, col, dnr, y in bags:
        draw.text((60, y), bid, fill='#38bdf8', font=get_font(10, True))
        draw.text((170, y), bg, fill='#f43f5e', font=get_font(10, True))
        draw.text((290, y), cd, fill='#cbd5e1', font=get_font(10))
        draw.text((430, y), ed, fill='#cbd5e1', font=get_font(10))
        draw.text((580, y), dl, fill=col, font=get_font(10, True))
        draw.text((710, y), st, fill='#34d399', font=get_font(10, True))
        draw.text((820, y), dnr, fill='#94a3b8', font=get_font(10))
    
    img.save('report_assets/fig_3_3_stock_inventory.png')
    print('Generated fig_3_3_stock_inventory.png')

# FIG 3.4: Hospital Requests
def make_fig_3_4():
    w, h = 950, 520
    img = Image.new('RGB', (w, h), color='#0f172a')
    draw = ImageDraw.Draw(img)
    draw_header(draw, w, 'Hospital Emergency Blood Request Interface', 'Hospital: Apollo Speciality (HOSP101)')
    
    # Left Request Submission Form
    draw.rectangle([30, 75, 450, 500], fill='#1e293b', outline='#3b82f6', width=2)
    draw.text((50, 95), 'Create Emergency Blood Request', fill='#ffffff', font=get_font(16, True))
    
    draw.text((50, 135), 'Required Blood Group', fill='#94a3b8', font=get_font(12))
    draw.rectangle([50, 155, 430, 190], fill='#0f172a', outline='#475569')
    draw.text((65, 165), 'O+ (O Positive)', fill='#ffffff', font=get_font(12))
    
    draw.text((50, 205), 'Required Units (Bags)', fill='#94a3b8', font=get_font(12))
    draw.rectangle([50, 225, 430, 260], fill='#0f172a', outline='#475569')
    draw.text((65, 235), '4 Units', fill='#ffffff', font=get_font(12))
    
    draw.text((50, 275), 'Urgency Level / SLA Window', fill='#94a3b8', font=get_font(12))
    draw.rectangle([50, 295, 430, 330], fill='#7f1d1d', outline='#ef4444')
    draw.text((65, 305), 'HIGH PRIORITY (Critical Surgery - 2 Hours SLA)', fill='#ffffff', font=get_font(11, True))
    
    draw.text((50, 345), 'Clinical Reason / Patient Details', fill='#94a3b8', font=get_font(12))
    draw.rectangle([50, 365, 430, 420], fill='#0f172a', outline='#475569')
    draw.text((65, 375), 'Emergency Trauma Unit - ICU Bed #4\nImmediate blood transfusion needed.', fill='#cbd5e1', font=get_font(11))
    
    draw.rectangle([50, 440, 430, 480], fill='#2563eb')
    draw.text((150, 452), 'Submit Emergency Request', fill='#ffffff', font=get_font(13, True))
    
    # Right Request History Ledger
    draw.rectangle([470, 75, 920, 500], fill='#1e293b', outline='#334155')
    draw.text((490, 95), 'Hospital Request History & Real-Time Tracking', fill='#ffffff', font=get_font(16, True))
    
    draw.rectangle([490, 130, 900, 160], fill='#334155')
    draw.text((505, 138), 'REQ ID', fill='#cbd5e1', font=get_font(11, True))
    draw.text((580, 138), 'GROUP', fill='#cbd5e1', font=get_font(11, True))
    draw.text((650, 138), 'UNITS', fill='#cbd5e1', font=get_font(11, True))
    draw.text((720, 138), 'URGENCY', fill='#cbd5e1', font=get_font(11, True))
    draw.text((820, 138), 'STATUS', fill='#cbd5e1', font=get_font(11, True))
    
    reqs = [
        ('REQ-1042', 'O+', '4 Units', 'HIGH (2h)', 'PENDING', '#ef4444', 180),
        ('REQ-1038', 'A+', '2 Units', 'MEDIUM (4h)', 'APPROVED', '#10b981', 230),
        ('REQ-1035', 'B+', '3 Units', 'LOW (8h)', 'COMPLETED', '#3b82f6', 280),
        ('REQ-1029', 'AB+', '1 Unit', 'LOW (8h)', 'REJECTED', '#64748b', 330)
    ]
    for rid, bg, u, urg, st, col, y in reqs:
        draw.text((505, y), rid, fill='#38bdf8', font=get_font(11, True))
        draw.text((580, y), bg, fill='#f43f5e', font=get_font(11, True))
        draw.text((650, y), u, fill='#ffffff', font=get_font(11))
        draw.text((720, y), urg, fill='#f59e0b', font=get_font(11))
        draw.rectangle([815, y - 2, 895, y + 20], fill=col)
        draw.text((825, y + 2), st, fill='#ffffff', font=get_font(10, True))
    
    draw.rectangle([490, 390, 900, 480], fill='#0f172a', outline='#334155')
    draw.text((505, 405), 'SLA Warning Notice:', fill='#38bdf8', font=get_font(12, True))
    draw.text((505, 430), 'High priority requests are auto-escalated on the Super Admin console\nand FIFO-matched against earliest-expiring usable stock.', fill='#94a3b8', font=get_font(11))
    
    img.save('report_assets/fig_3_4_hospital_requests.png')
    print('Generated fig_3_4_hospital_requests.png')

# FIG 3.5: FIFO Approval Modal
def make_fig_3_5():
    w, h = 950, 520
    img = Image.new('RGB', (w, h), color='#0f172a')
    draw = ImageDraw.Draw(img)
    draw_header(draw, w, 'Admin FIFO Blood Allocation & Approval Engine', 'Earliest-Expiry-First Algorithm')
    
    # Background dimmed table
    draw.rectangle([30, 70, 920, 160], fill='#1e293b', outline='#334155')
    draw.text((45, 80), 'Request Details: REQ-1042 (Apollo Hospital) - 4 Units O+ Blood Requested', fill='#ffffff', font=get_font(14, True))
    draw.text((45, 110), 'Urgency: HIGH (2 Hours SLA) | Patient: Trauma ICU Bed 4 | Request Date: 2025-10-09 10:15 AM', fill='#cbd5e1', font=get_font(12))
    draw.text((45, 135), 'Usable Stock for O+: 42 Units Available in Bank', fill='#34d399', font=get_font(12, True))
    
    # FIFO Allocation Modal
    draw.rectangle([120, 180, 830, 495], fill='#1e293b', outline='#e11d48', width=2)
    draw.rectangle([120, 180, 830, 220], fill='#881337')
    draw.text((140, 192), 'FIFO Earliest-Expiry-First Automatic Allocation', fill='#ffffff', font=get_font(15, True))
    
    draw.text((140, 235), 'The system sorted all available O+ units by expiry date and selected the earliest-expiring bags:', fill='#cbd5e1', font=get_font(12))
    
    # Allocated Bags Table
    draw.rectangle([140, 265, 810, 295], fill='#334155')
    draw.text((160, 273), 'SERIAL #', fill='#cbd5e1', font=get_font(10, True))
    draw.text((260, 273), 'BAG ID', fill='#cbd5e1', font=get_font(10, True))
    draw.text((380, 273), 'COLLECTION DATE', fill='#cbd5e1', font=get_font(10, True))
    draw.text((530, 273), 'EXPIRY DATE', fill='#cbd5e1', font=get_font(10, True))
    draw.text((680, 273), 'SHELF LIFE LEFT', fill='#cbd5e1', font=get_font(10, True))
    
    alloc_bags = [
        ('1', 'BAG10012', '2025-09-18', '2025-10-23', '14 Days remaining', 305),
        ('2', 'BAG10015', '2025-09-20', '2025-10-25', '16 Days remaining', 335),
        ('3', 'BAG10018', '2025-09-22', '2025-10-27', '18 Days remaining', 365),
        ('4', 'BAG10022', '2025-09-25', '2025-10-30', '21 Days remaining', 395)
    ]
    for s, bid, cd, ed, rem, y in alloc_bags:
        draw.text((170, y), s, fill='#ffffff', font=get_font(10))
        draw.text((260, y), bid, fill='#38bdf8', font=get_font(10, True))
        draw.text((380, y), cd, fill='#cbd5e1', font=get_font(10))
        draw.text((530, y), ed, fill='#f43f5e', font=get_font(10, True))
        draw.text((680, y), rem, fill='#f59e0b', font=get_font(10))
    
    # Financial Calculation Note
    draw.text((140, 430), 'Base Price: 4 x Rs. 1,400 = Rs. 5,600 | 5% GST: Rs. 280 | Invoice Total: Rs. 5,880', fill='#34d399', font=get_font(11, True))
    
    # Action Buttons
    draw.rectangle([140, 455, 380, 485], fill='#10b981')
    draw.text((160, 463), 'Confirm Full Approval & Dispatch', fill='#ffffff', font=get_font(11, True))
    
    draw.rectangle([400, 455, 590, 485], fill='#f59e0b')
    draw.text((420, 463), 'Partial Approval (2 Units)', fill='#ffffff', font=get_font(11, True))
    
    draw.rectangle([610, 455, 750, 485], fill='#ef4444')
    draw.text((645, 463), 'Reject', fill='#ffffff', font=get_font(11, True))
    
    img.save('report_assets/fig_3_5_fifo_approval.png')
    print('Generated fig_3_5_fifo_approval.png')

# FIG 3.6: Coordinator Donor Eligibility
def make_fig_3_6():
    w, h = 950, 520
    img = Image.new('RGB', (w, h), color='#0f172a')
    draw = ImageDraw.Draw(img)
    draw_header(draw, w, 'Coordinator Portal - Live Donor Screening & Eligibility Evaluation', 'Staff: coord@bloodbank.org')
    
    # Left Registration Form
    draw.rectangle([30, 75, 460, 500], fill='#1e293b', outline='#10b981', width=2)
    draw.text((50, 90), 'Donor Medical Screening Form', fill='#ffffff', font=get_font(15, True))
    
    fields = [
        ('Full Name', 'Rajesh Kumar S', 120),
        ('Age (Mandatory: 18 - 60 Years)', '26 Years', 170),
        ('Weight (Mandatory: >= 45 kg)', '68 kg', 220),
        ('Blood Group', 'O+ (Positive)', 270),
        ('Last Donation Date (Mandatory: 4 Month Interval)', '2025-05-10 (5 Months Ago)', 320),
        ('Active Medical Conditions / Medications', 'None / Healthy', 370)
    ]
    for label, val, y in fields:
        draw.text((50, y), label, fill='#94a3b8', font=get_font(10))
        draw.rectangle([50, y + 16, 440, y + 40], fill='#0f172a', outline='#475569')
        draw.text((60, y + 22), val, fill='#ffffff', font=get_font(11))
    
    draw.rectangle([50, 445, 440, 485], fill='#10b981')
    draw.text((140, 457), 'Evaluate & Register Donor', fill='#ffffff', font=get_font(13, True))
    
    # Right Live Eligibility Result Card
    draw.rectangle([480, 75, 920, 270], fill='#1e293b', outline='#34d399', width=2)
    draw.text((500, 90), 'Live Medical Eligibility Verdict', fill='#ffffff', font=get_font(15, True))
    
    draw.rectangle([500, 120, 900, 160], fill='#064e3b')
    draw.text((520, 132), 'STATUS: ELIGIBLE TO DONATE BLOOD', fill='#34d399', font=get_font(14, True))
    
    criteria = [
        ('Age Check (18-60):', '26 Years -> PASSED (Valid)', '#10b981'),
        ('Weight Check (>=45kg):', '68 kg -> PASSED (Valid)', '#10b981'),
        ('Donation Interval Check:', '152 Days (>120 Days / 4 Mo) -> PASSED', '#10b981'),
        ('Health Conditions Check:', 'No contraindications -> PASSED', '#10b981')
    ]
    for i, (c_name, c_res, col) in enumerate(criteria):
        draw.text((500, 175 + i * 22), c_name, fill='#cbd5e1', font=get_font(11))
        draw.text((700, 175 + i * 22), c_res, fill=col, font=get_font(11, True))
    
    # Recent Donors Table
    draw.rectangle([480, 285, 920, 500], fill='#1e293b', outline='#334155')
    draw.text((500, 300), 'Recently Registered Donors Registry', fill='#ffffff', font=get_font(13, True))
    
    draw.rectangle([500, 330, 900, 355], fill='#334155')
    draw.text((515, 336), 'DONOR ID', fill='#cbd5e1', font=get_font(10, True))
    draw.text((600, 336), 'NAME', fill='#cbd5e1', font=get_font(10, True))
    draw.text((710, 336), 'BLOOD GROUP', fill='#cbd5e1', font=get_font(10, True))
    draw.text((820, 336), 'ELIGIBILITY', fill='#cbd5e1', font=get_font(10, True))
    
    dnrs = [
        ('DNR-5012', 'Rajesh Kumar S', 'O+', 'ELIGIBLE', '#10b981', 365),
        ('DNR-5011', 'Priya Dharshini', 'A+', 'ELIGIBLE', '#10b981', 395),
        ('DNR-5010', 'Karthik V', 'B-', 'INELIGIBLE (<4mo)', '#ef4444', 425),
        ('DNR-5009', 'Anand M', 'AB+', 'ELIGIBLE', '#10b981', 455)
    ]
    for did, dname, bg, el, col, y in dnrs:
        draw.text((515, y), did, fill='#38bdf8', font=get_font(10, True))
        draw.text((600, y), dname, fill='#ffffff', font=get_font(10))
        draw.text((710, y), bg, fill='#f43f5e', font=get_font(10, True))
        draw.text((820, y), el, fill=col, font=get_font(10, True))
    
    img.save('report_assets/fig_3_6_donor_eligibility.png')
    print('Generated fig_3_6_donor_eligibility.png')

# FIG 3.7: Donation Logging & Bag Gen
def make_fig_3_7():
    w, h = 950, 520
    img = Image.new('RGB', (w, h), color='#0f172a')
    draw = ImageDraw.Draw(img)
    draw_header(draw, w, 'Blood Collection & Automatic Bag Generation Engine', 'Coordinator Workflow')
    
    # Left Collection Form
    draw.rectangle([30, 75, 450, 500], fill='#1e293b', outline='#e11d48', width=2)
    draw.text((50, 90), 'Record Blood Donation Event', fill='#ffffff', font=get_font(15, True))
    
    draw.text((50, 125), 'Select Registered Donor', fill='#94a3b8', font=get_font(11))
    draw.rectangle([50, 145, 430, 180], fill='#0f172a', outline='#475569')
    draw.text((65, 155), 'DNR-5012: Rajesh Kumar S (O+)', fill='#38bdf8', font=get_font(12, True))
    
    draw.text((50, 195), 'Collection Volume & Type', fill='#94a3b8', font=get_font(11))
    draw.rectangle([50, 215, 430, 250], fill='#0f172a', outline='#475569')
    draw.text((65, 225), '450 ml Whole Blood Standard Bag', fill='#ffffff', font=get_font(12))
    
    draw.text((50, 265), 'Collection Timestamp', fill='#94a3b8', font=get_font(11))
    draw.rectangle([50, 285, 430, 320], fill='#0f172a', outline='#475569')
    draw.text((65, 295), '2025-10-09 11:30 AM (Today)', fill='#ffffff', font=get_font(12))
    
    draw.text((50, 335), 'Coordinator In-Charge', fill='#94a3b8', font=get_font(11))
    draw.rectangle([50, 355, 430, 390], fill='#0f172a', outline='#475569')
    draw.text((65, 365), 'coord@bloodbank.org (Staff ID #8)', fill='#ffffff', font=get_font(12))
    
    draw.rectangle([50, 420, 430, 470], fill='#e11d48')
    draw.text((100, 435), 'Generate Blood Bag & Log Stock', fill='#ffffff', font=get_font(13, True))
    
    # Right Auto Bag Generation Card
    draw.rectangle([470, 75, 920, 275], fill='#1e293b', outline='#38bdf8', width=2)
    draw.text((490, 90), 'Generated Blood Bag Unit Details', fill='#ffffff', font=get_font(15, True))
    
    # Generated Bag Badge
    draw.rectangle([490, 120, 900, 160], fill='#0369a1')
    draw.text((510, 132), 'UNIQUE BAG BARCODE: BAG10046 (Auto-Sequenced)', fill='#ffffff', font=get_font(13, True))
    
    details = [
        ('Blood Group:', 'O+ (Rh Positive)'),
        ('Collection Date:', '2025-10-09'),
        ('Computed Expiry Date:', '2025-11-13 (Exact 35 Days Shelf Life)'),
        ('Storage Location:', 'Refrigerated Unit #3 (2 deg C - 6 deg C)'),
        ('Donor Eligibility Update:', 'Donor locked until 2026-02-09 (4 Months)')
    ]
    for i, (k, v) in enumerate(details):
        draw.text((490, 175 + i * 20), k, fill='#94a3b8', font=get_font(10))
        draw.text((660, 175 + i * 20), v, fill='#34d399' if 'Expiry' in k or 'locked' in v else '#ffffff', font=get_font(10, True))
    
    # Verification Info Box
    draw.rectangle([470, 290, 920, 500], fill='#1e293b', outline='#334155')
    draw.text((490, 305), 'Automated Integrity & Safety Rules Triggered', fill='#ffffff', font=get_font(13, True))
    draw.text((490, 335), '1. Atomic Counter Increment: Counter `bag_id` incremented safely in MongoDB.\n2. Expiry Timestamping: `expiry_date` computed using UTC datetime addition.\n3. Inventory Usable Units: Group O+ usable units incremented by +1 automatically.\n4. Donor Cooldown Enforced: Donor DNR-5012 marked as ineligible for next 120 days.\n5. Audit Log Recorded: Timestamp, coordinator ID, and bag barcode stored for compliance.', fill='#cbd5e1', font=get_font(11))
    
    img.save('report_assets/fig_3_7_donation_bag_gen.png')
    print('Generated fig_3_7_donation_bag_gen.png')

# FIG 3.8: Hospital Billing & Payment
def make_fig_3_8():
    w, h = 950, 520
    img = Image.new('RGB', (w, h), color='#0f172a')
    draw = ImageDraw.Draw(img)
    draw_header(draw, w, 'Hospital Billing Ledger & Automated 5% GST Invoicing', 'Reconciliation Module')
    
    # Financial Overview Cards
    draw.rectangle([30, 70, 460, 150], fill='#1e293b', outline='#f59e0b', width=2)
    draw.text((45, 80), 'HOSPITAL OUTSTANDING BALANCE', fill='#94a3b8', font=get_font(10, True))
    draw.text((45, 100), 'Rs. 14,700.00', fill='#f59e0b', font=get_font(20, True))
    draw.text((45, 128), 'Apollo Speciality Hospital (HOSP101) - 2 Unpaid Invoices', fill='#cbd5e1', font=get_font(10))
    
    draw.rectangle([480, 70, 920, 150], fill='#1e293b', outline='#10b981', width=2)
    draw.text((495, 80), 'LIFETIME SETTLED PAYMENTS', fill='#94a3b8', font=get_font(10, True))
    draw.text((495, 100), 'Rs. 92,400.00', fill='#10b981', font=get_font(20, True))
    draw.text((495, 128), '14 Invoices Fully Paid & Reconciled', fill='#cbd5e1', font=get_font(10))
    
    # Invoice Ledger Table
    draw.rectangle([30, 165, 920, 360], fill='#1e293b', outline='#334155')
    draw.text((45, 175), 'Automated Invoice Ledger & 5% GST Breakdown', fill='#ffffff', font=get_font(13, True))
    
    draw.rectangle([45, 200, 905, 225], fill='#334155')
    headers = [('INVOICE #', 60), ('DATE', 160), ('ITEMS / BLOOD', 260), ('SUBTOTAL', 430), ('5% GST', 540), ('TOTAL', 640), ('STATUS', 740), ('ACTION', 830)]
    for h_txt, h_x in headers:
        draw.text((h_x, 206), h_txt, fill='#cbd5e1', font=get_font(10, True))
    
    invoices = [
        ('INV-8821', '2025-10-09', '4 Bags O+ (REQ-1042)', 'Rs. 5,600', 'Rs. 280', 'Rs. 5,880', 'UNPAID', '#ef4444', 235),
        ('INV-8818', '2025-10-06', '6 Bags A+ (REQ-1038)', 'Rs. 8,400', 'Rs. 420', 'Rs. 8,820', 'UNPAID', '#ef4444', 265),
        ('INV-8805', '2025-09-28', '2 Bags B+ (REQ-1031)', 'Rs. 2,400', 'Rs. 120', 'Rs. 2,520', 'PAID', '#10b981', 295),
        ('INV-8799', '2025-09-22', '5 Bags O- (REQ-1025)', 'Rs. 10,000', 'Rs. 500', 'Rs. 10,500', 'PAID', '#10b981', 325)
    ]
    for inv_id, dt, items, sub, tax, tot, st, col, y in invoices:
        draw.text((60, y), inv_id, fill='#38bdf8', font=get_font(10, True))
        draw.text((160, y), dt, fill='#cbd5e1', font=get_font(10))
        draw.text((260, y), items, fill='#ffffff', font=get_font(10))
        draw.text((430, y), sub, fill='#cbd5e1', font=get_font(10))
        draw.text((540, y), tax, fill='#cbd5e1', font=get_font(10))
        draw.text((640, y), tot, fill='#34d399', font=get_font(10, True))
        draw.rectangle([735, y - 2, 805, y + 18], fill=col)
        draw.text((745, y), st, fill='#ffffff', font=get_font(9, True))
        draw.rectangle([825, y - 2, 895, y + 18], fill='#2563eb' if st=='UNPAID' else '#475569')
        draw.text((835, y), 'Pay Now' if st=='UNPAID' else 'Receipt', fill='#ffffff', font=get_font(9, True))
    
    # Payment Settlement Modal Preview
    draw.rectangle([30, 375, 920, 500], fill='#1e293b', outline='#3b82f6')
    draw.text((45, 388), 'Hospital Digital Payment Reconciliation Modal Preview', fill='#ffffff', font=get_font(13, True))
    draw.text((45, 415), '- Target Invoice: INV-8821 | Amount: Rs. 5,880.00 (Including 5% GST: Rs. 280.00)\n- Payment Method: Electronic Fund Transfer (NEFT / RTGS / UPI) | Transaction Ref: TXN-99824177\n- Real-Time Ledger Sync: Validates payment amount >= invoice total, marks invoice as PAID, and deducts Rs. 5,880 from hospital balance.\n- Formatted Printable Audit Invoice generated with hospital GSTIN and timestamp.', fill='#cbd5e1', font=get_font(11))
    
    img.save('report_assets/fig_3_8_hospital_billing.png')
    print('Generated fig_3_8_hospital_billing.png')

if __name__ == '__main__':
    make_fig_3_1()
    make_fig_3_2()
    make_fig_3_3()
    make_fig_3_4()
    make_fig_3_5()
    make_fig_3_6()
    make_fig_3_7()
    make_fig_3_8()
    print('All 8 figures generated successfully!')
