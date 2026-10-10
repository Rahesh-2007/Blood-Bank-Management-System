/**
 * Hospital Portal Controller
 */

let currentSection = 'my-requests';
let activePaymentInvoice = null;

document.addEventListener('DOMContentLoaded', async () => {
  // Check auth
  const authRes = await API.getCurrentUser();
  if (!authRes.authenticated || authRes.user.role !== 'HOSPITAL') {
    window.location.href = '/';
    return;
  }

  const u = authRes.user;
  document.getElementById('hosp-user-name').innerText = u.hospital_name || u.name || 'Hospital Authority';
  const idEl = document.getElementById('hosp-id-display');
  if (idEl) idEl.innerText = u.hospital_id || '';

  setupHospitalSidebar();
  setupNewRequestForm();
  loadHospitalRequests();
  loadHospitalInvoices();
  loadHospitalStockView();
  loadHospitalBalance();
});

function setupHospitalSidebar() {
  const items = document.querySelectorAll('.sidebar-nav .nav-item');
  items.forEach(item => {
    item.addEventListener('click', () => {
      items.forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      const target = item.dataset.section;
      showHospitalSection(target);
    });
  });
}

function showHospitalSection(sectionId) {
  currentSection = sectionId;
  document.querySelectorAll('.hosp-section').forEach(sec => sec.style.display = 'none');
  const targetSec = document.getElementById(`section-${sectionId}`);
  if (targetSec) targetSec.style.display = 'block';

  // Highlight active nav
  document.querySelectorAll('.sidebar-nav .nav-item').forEach(i => {
    i.classList.toggle('active', i.dataset.section === sectionId);
  });

  if (sectionId === 'my-requests') {
    loadHospitalRequests();
  } else if (sectionId === 'invoices') {
    loadHospitalInvoices();
  } else if (sectionId === 'stock-view') {
    loadHospitalStockView();
  } else if (sectionId === 'profile') {
    loadUserProfile();
  }
}

// 1. Live Balance & Stats
async function loadHospitalBalance() {
  const res = await API.get('/api/profile/me');
  if (res.success && res.profile) {
    const bal = res.profile.outstanding_balance || 0;
    const badgeEl = document.getElementById('hosp-balance-badge');
    if (badgeEl) {
      badgeEl.innerText = formatCurrency(bal);
      badgeEl.className = bal > 0 ? 'font-mono font-bold text-danger' : 'font-mono font-bold text-success';
    }
  }
}

// 2. New Blood Request Form
function setupNewRequestForm() {
  const form = document.getElementById('new-blood-request-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('submit-req-btn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Submitting Request...'; }

    const payload = {
      blood_group: document.getElementById('req-blood-group').value,
      quantity: parseInt(document.getElementById('req-quantity').value, 10),
      emergency_level: document.getElementById('req-emergency').value,
      notes: document.getElementById('req-notes').value.trim()
    };

    const res = await API.post('/api/requests/create', payload);
    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Submit Emergency Blood Request'; }

    if (res.success) {
      showToast('Request Submitted', res.message, 'success');
      form.reset();
      showHospitalSection('my-requests');
      loadHospitalRequests();
    } else {
      showToast('Error', res.message, 'error');
    }
  });
}

// 3. My Requests Tracker
async function loadHospitalRequests() {
  const res = await API.get('/api/requests');
  const tbody = document.getElementById('hosp-requests-table-body');
  if (!tbody || !res.success) return;

  const reqs = res.requests || [];
  if (reqs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted" style="padding:2.5rem;">You have not created any blood requests yet. Click "New Request" above to initiate one.</td></tr>`;
    return;
  }

  tbody.innerHTML = reqs.map(r => {
    const isPending = (r.status === 'Pending' || r.status === 'Partially Approved');
    const timeRemainingHtml = r.is_overdue
      ? `<span class="badge badge-danger"><i class="fa-solid fa-triangle-exclamation"></i> OVERDUE</span>`
      : `<span class="font-mono text-xs ${r.seconds_remaining < 3600 ? 'text-danger font-bold' : 'text-muted'}"><i class="fa-regular fa-clock"></i> ${escapeHtml(r.time_remaining_formatted || 'N/A')}</span>`;

    const remaining = r.remaining_quantity ?? (r.quantity - (r.approved_quantity || 0));

    return `
      <tr>
        <td class="font-mono font-bold">${escapeHtml(r.request_id)}</td>
        <td><span class="badge badge-primary font-mono font-bold text-md">${escapeHtml(r.blood_group)}</span></td>
        <td>
          <div class="font-mono"><strong>${r.quantity}</strong> units requested</div>
          <div class="text-xs text-muted">Issued: <strong>${r.approved_quantity || 0}</strong> | Remaining: <strong class="text-danger">${remaining}</strong></div>
        </td>
        <td>${getBadgeHTML(r.emergency_level)}</td>
        <td>${timeRemainingHtml}</td>
        <td>${getBadgeHTML(r.status)}</td>
        <td class="text-xs text-muted">${formatDateTime(r.created_at)}</td>
        <td>
          ${isPending ? `
            <button class="btn btn-outline-danger btn-sm" onclick="cancelHospitalRequest('${r.request_id}')">
              <i class="fa-solid fa-ban"></i> Cancel
            </button>
          ` : `
            <span class="text-xs text-muted font-medium"><i class="fa-solid fa-circle-check text-success"></i> Done</span>
          `}
        </td>
      </tr>
    `;
  }).join('');
}

async function cancelHospitalRequest(requestId) {
  if (!confirm(`Are you sure you want to cancel blood request ${requestId}?`)) return;

  const res = await API.post(`/api/requests/${requestId}/cancel`);
  if (res.success) {
    showToast('Cancelled', res.message, 'success');
    loadHospitalRequests();
  } else {
    showToast('Error', res.message, 'error');
  }
}

// 4. Invoices & Online Demo Payment
async function loadHospitalInvoices() {
  const res = await API.get('/api/invoices');
  const tbody = document.getElementById('hosp-invoices-table-body');
  if (!tbody || !res.success) return;

  const invoices = res.invoices || [];
  if (invoices.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted" style="padding:2.5rem;">No invoices issued to your hospital account yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = invoices.map(i => {
    const isUnpaid = (i.status === 'PENDING');
    return `
      <tr>
        <td class="font-mono font-bold">${escapeHtml(i.invoice_number)}</td>
        <td class="font-mono text-xs">${escapeHtml(i.request_id)}</td>
        <td><span class="badge badge-primary font-mono">${escapeHtml(i.blood_group)}</span></td>
        <td class="font-mono">${i.quantity} Bag(s)</td>
        <td class="font-mono text-xs">₹${Number(i.subtotal).toLocaleString('en-IN')}</td>
        <td class="font-mono text-xs">₹${Number(i.tax_amount).toLocaleString('en-IN')}</td>
        <td class="font-mono font-bold text-gradient">${formatCurrency(i.total_amount)}</td>
        <td>${getBadgeHTML(i.status)}</td>
        <td>
          <div style="display:flex; gap:0.4rem;">
            <button class="btn btn-secondary btn-sm" onclick="openHospitalInvoiceDetail('${i.invoice_number}')">
              <i class="fa-solid fa-eye"></i> View
            </button>
            ${isUnpaid ? `
              <button class="btn btn-success btn-sm" onclick="openPaymentModal('${i.invoice_number}', ${i.total_amount})">
                <i class="fa-solid fa-credit-card"></i> Pay Now
              </button>
            ` : `
              <span class="text-xs text-success font-bold" style="padding:4px 8px;"><i class="fa-solid fa-check-double"></i> Cleared</span>
            `}
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

async function openHospitalInvoiceDetail(invNumber) {
  const res = await API.get(`/api/invoices/${invNumber}`);
  if (!res.success || !res.invoice) {
    showToast('Error', 'Unable to fetch invoice details.', 'error');
    return;
  }

  const i = res.invoice;
  const h = res.hospital || {};

  document.getElementById('modal-inv-number').innerText = i.invoice_number;
  document.getElementById('modal-inv-date').innerText = formatDate(i.invoice_date);
  document.getElementById('modal-inv-status').innerHTML = getBadgeHTML(i.status);

  document.getElementById('modal-inv-hospital-name').innerText = h.name || i.hospital_name;
  document.getElementById('modal-inv-hospital-email').innerText = h.email || '';
  document.getElementById('modal-inv-hospital-address').innerText = h.address || '';

  document.getElementById('modal-inv-req-id').innerText = i.request_id;
  document.getElementById('modal-inv-blood-group').innerText = i.blood_group;
  document.getElementById('modal-inv-quantity').innerText = `${i.quantity} Bag(s)`;

  document.getElementById('modal-inv-bags').innerText = (i.blood_bags || []).join(', ') || 'N/A';

  document.getElementById('modal-inv-unit-price').innerText = `₹${Number(i.unit_price || 2500).toLocaleString('en-IN')}`;
  document.getElementById('modal-inv-subtotal').innerText = `₹${Number(i.subtotal).toLocaleString('en-IN')}`;
  document.getElementById('modal-inv-tax').innerText = `₹${Number(i.tax_amount).toLocaleString('en-IN')}`;
  document.getElementById('modal-inv-total').innerText = formatCurrency(i.total_amount);

  document.getElementById('invoice-detail-modal').classList.add('active');
}

function closeInvoiceModal() {
  document.getElementById('invoice-detail-modal').classList.remove('active');
}

function openPaymentModal(invNumber, amount) {
  activePaymentInvoice = { invoice_number: invNumber, amount: amount };

  let modal = document.getElementById('payment-checkout-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'payment-checkout-modal';
    modal.className = 'modal-backdrop';
    document.body.appendChild(modal);
  }

  modal.innerHTML = `
    <div class="modal-dialog" style="max-width:500px;">
      <div class="modal-header">
        <h4><i class="fa-solid fa-credit-card text-success"></i> Settle Invoice: ${escapeHtml(invNumber)}</h4>
        <button class="btn-icon btn-secondary" onclick="document.getElementById('payment-checkout-modal').classList.remove('active')">&times;</button>
      </div>
      <form id="payment-checkout-form" onsubmit="submitInvoicePayment(event)">
        <div class="modal-body">
          <div style="background:#f8fafc; border:1px solid var(--border-color); border-radius:10px; padding:1.25rem; margin-bottom:1.25rem; text-align:center;">
            <div class="text-xs text-muted font-bold text-uppercase">Total Payable Amount</div>
            <h2 class="text-gradient font-mono font-bold" style="font-size:2rem; margin:0.35rem 0;">${formatCurrency(amount)}</h2>
            <div class="text-xs text-muted">Includes blood unit base charges + 5% standard GST</div>
          </div>

          <div class="form-group">
            <label class="form-label">Select Payment Method</label>
            <select id="pay-method" class="form-select">
              <option value="Online Bank Transfer / NEFT">Online Bank Transfer / NEFT</option>
              <option value="Hospital Corporate Card">Hospital Corporate Card</option>
              <option value="Direct Institutional Clearance (Demo)">Direct Institutional Clearance (Demo)</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Payment Amount (INR)</label>
            <input type="number" id="pay-amount" class="form-control font-mono font-bold" value="${amount}" step="0.01" readonly style="background:#f1f5f9;">
          </div>

          <div class="info-inset-box text-xs text-muted" style="margin-top:0.75rem;">
            <i class="fa-solid fa-shield-halved text-success"></i> <strong>Safe Checkout:</strong> This transaction will clear invoice ${escapeHtml(invNumber)} and reduce your outstanding hospital balance instantly.
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" onclick="document.getElementById('payment-checkout-modal').classList.remove('active')">Cancel</button>
          <button type="submit" id="btn-confirm-payment" class="btn btn-success"><i class="fa-solid fa-lock"></i> Authorize & Pay ${formatCurrency(amount)}</button>
        </div>
      </form>
    </div>
  `;
  modal.classList.add('active');
}

async function submitInvoicePayment(e) {
  e.preventDefault();
  if (!activePaymentInvoice) return;

  const btn = document.getElementById('btn-confirm-payment');
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing Payment...'; }

  const payload = {
    payment_amount: parseFloat(document.getElementById('pay-amount').value),
    payment_method: document.getElementById('pay-method').value
  };

  const res = await API.post(`/api/invoices/${activePaymentInvoice.invoice_number}/pay`, payload);
  if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-lock"></i> Authorize Payment'; }

  if (res.success) {
    showToast('Payment Successful', res.message, 'success');
    document.getElementById('payment-checkout-modal').classList.remove('active');
    loadHospitalInvoices();
    loadHospitalBalance();
  } else {
    showToast('Payment Failed', res.message, 'error');
  }
}

// 5. Stock View
async function loadHospitalStockView() {
  const res = await API.get('/api/stock/summary');
  const container = document.getElementById('hosp-stock-cards');
  if (!container || !res.success) return;

  container.innerHTML = (res.groups || []).map(g => `
    <div class="stock-card">
      <div class="blood-type">${escapeHtml(g.blood_group)}</div>
      <div class="stock-condition-group">
        ${g.is_out_of_stock ? '<span class="stock-condition-item out-of-stock">0 Available</span>' : `<span class="stock-condition-item good">${g.available_count} Available</span>`}
      </div>
      <div class="stock-price">₹${Number(g.price_per_unit).toLocaleString('en-IN')}/bag</div>
    </div>
  `).join('');
}
