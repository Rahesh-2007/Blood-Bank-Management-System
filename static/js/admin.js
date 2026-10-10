/**
 * Super Admin Dashboard Controller
 */

let currentSection = 'overview';
let activeProcessRequest = null;

document.addEventListener('DOMContentLoaded', async () => {
  // Check auth
  const authRes = await API.getCurrentUser();
  if (!authRes.authenticated || authRes.user.role !== 'ADMIN') {
    window.location.href = '/';
    return;
  }
  document.getElementById('admin-user-name').innerText = authRes.user.name || 'Super Admin';

  setupSidebarNav();
  loadAllAdminData();

  // Periodic refresh every 20 seconds
  setInterval(() => {
    if (currentSection === 'overview' || currentSection === 'requests' || currentSection === 'stock') {
      loadStockSummary();
      loadBloodRequests();
    }
  }, 20000);
});

function setupSidebarNav() {
  const items = document.querySelectorAll('.sidebar-nav .nav-item');
  items.forEach(item => {
    item.addEventListener('click', () => {
      items.forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      const target = item.dataset.section;
      showSection(target);
    });
  });
}

function showSection(sectionId) {
  currentSection = sectionId;
  document.querySelectorAll('.admin-section').forEach(sec => sec.style.display = 'none');
  const targetSec = document.getElementById(`section-${sectionId}`);
  if (targetSec) targetSec.style.display = 'block';

  // Highlight active nav
  document.querySelectorAll('.sidebar-nav .nav-item').forEach(i => {
    i.classList.toggle('active', i.dataset.section === sectionId);
  });

  if (sectionId === 'overview') {
    loadDashboardStats();
    loadStockSummary();
    loadBloodRequests();
  } else if (sectionId === 'requests') {
    loadBloodRequests();
  } else if (sectionId === 'stock') {
    loadStockSummary();
    loadBloodBags();
  } else if (sectionId === 'donors') {
    loadDonorsList();
  } else if (sectionId === 'entities') {
    loadHospitalsList();
    loadCoordinatorsList();
  } else if (sectionId === 'invoices') {
    loadInvoicesList();
  } else if (sectionId === 'alerts') {
    loadInventoryAlerts();
  } else if (sectionId === 'reports') {
    loadActivityAuditLog();
  } else if (sectionId === 'profile') {
    loadUserProfile();
  }
}

async function loadAllAdminData() {
  await Promise.all([
    loadDashboardStats(),
    loadStockSummary(),
    loadBloodRequests(),
    loadBloodBags(),
    loadDonorsList(),
    loadHospitalsList(),
    loadCoordinatorsList(),
    loadInvoicesList()
  ]);
}

// 1. Dashboard Stats (4 Key Summary Cards)
async function loadDashboardStats() {
  const res = await API.get('/api/reports/dashboard-stats');
  if (res.success && res.stats) {
    const s = res.stats;
    const availEl = document.getElementById('stat-available-bags');
    const pendEl = document.getElementById('stat-pending-requests');
    const expEl = document.getElementById('stat-expiring-soon');
    const dueEl = document.getElementById('stat-outstanding-balance');

    if (availEl) availEl.innerText = s.inventory.available;
    if (pendEl) pendEl.innerText = s.requests.active;
    if (expEl) expEl.innerText = s.inventory.expiring_soon || 0;
    if (dueEl) dueEl.innerText = formatCurrency(s.finance.outstanding);
  }
}

// 2. Stock Summary (8 Blood Group Cards)
async function loadStockSummary() {
  const res = await API.get('/api/stock/summary');
  if (!res.success) return;

  const container = document.getElementById('stock-cards-container');
  const miniContainer = document.getElementById('overview-stock-cards');

  let html = '';
  res.groups.forEach(g => {
    let conditionHtml = '';
    if (g.is_out_of_stock) {
      conditionHtml = `<span class="stock-condition-item out-of-stock"><i class="fa-solid fa-circle-xmark"></i> Out of Stock (0)</span>`;
    } else {
      if (g.good_count > 0) {
        conditionHtml += `<span class="stock-condition-item good"><i class="fa-solid fa-circle-check"></i> Good: <strong>${g.good_count} ${g.good_count === 1 ? 'Bag' : 'Bags'}</strong></span>`;
      }
      if (g.critical_count > 0) {
        conditionHtml += `<span class="stock-condition-item critical"><i class="fa-solid fa-triangle-exclamation"></i> Critical: <strong>${g.critical_count} ${g.critical_count === 1 ? 'Bag' : 'Bags'}</strong></span>`;
      }
      if (g.is_low_stock && !g.is_out_of_stock) {
        conditionHtml += `<span class="stock-condition-item" style="background:#fff7ed; color:#c2410c; border:1px solid #fed7aa; font-size:0.72rem; padding:2px 6px;"><i class="fa-solid fa-bell"></i> Low Stock</span>`;
      }
    }

    html += `
      <div class="stock-card" onclick="filterBagsByGroup('${g.blood_group}')" style="cursor:pointer;" title="Click to filter individual bags">
        <div class="blood-type">${escapeHtml(g.blood_group)}</div>
        <div class="stock-condition-group">
          ${conditionHtml}
        </div>
        <div class="stock-price">₹${Number(g.price_per_unit).toLocaleString('en-IN')}/bag</div>
      </div>
    `;
  });

  if (container) container.innerHTML = html;
  if (miniContainer) miniContainer.innerHTML = html;
}

function filterBagsByGroup(bg) {
  showSection('stock');
  const sel = document.getElementById('filter-bag-group');
  if (sel) {
    sel.value = bg;
    loadBloodBags();
  }
}

// 3. Requests Management & FEFO Queue
async function loadBloodRequests() {
  const status = document.getElementById('filter-req-status')?.value || 'ALL';
  const emergency = document.getElementById('filter-req-urgency')?.value || 'ALL';

  const res = await API.get(`/api/requests?status=${status}&emergency=${emergency}`);
  if (!res.success) return;

  const reqs = res.requests || [];
  const overviewTbody = document.getElementById('overview-requests-table-body');
  const allTbody = document.getElementById('requests-table-body');

  const activeReqs = reqs.filter(r => r.status === 'Pending' || r.status === 'Partially Approved');

  if (overviewTbody) {
    if (activeReqs.length === 0) {
      overviewTbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted" style="padding:2rem;"><i class="fa-solid fa-circle-check text-success"></i> No active emergency requests awaiting dispatch. All requests fulfilled!</td></tr>`;
    } else {
      overviewTbody.innerHTML = activeReqs.map(r => renderRequestRow(r, true)).join('');
    }
  }

  if (allTbody) {
    if (reqs.length === 0) {
      allTbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted" style="padding:2rem;">No blood requests found.</td></tr>`;
    } else {
      allTbody.innerHTML = reqs.map(r => renderRequestRow(r, false)).join('');
    }
  }
}

function renderRequestRow(r, isOverview) {
  const isPending = (r.status === 'Pending' || r.status === 'Partially Approved');
  const urgencyBadge = getBadgeHTML(r.emergency_level);
  const statusBadge = getBadgeHTML(r.status);
  const timeRemainingHtml = r.is_overdue
    ? `<span class="badge badge-danger"><i class="fa-solid fa-circle-exclamation"></i> OVERDUE</span>`
    : `<span class="font-mono text-xs ${r.seconds_remaining < 3600 ? 'text-danger font-bold' : 'text-muted'}"><i class="fa-regular fa-clock"></i> ${escapeHtml(r.time_remaining_formatted || 'N/A')}</span>`;

  return `
    <tr>
      <td class="font-mono font-bold">${escapeHtml(r.request_id)}</td>
      <td>
        <div class="font-bold">${escapeHtml(r.hospital_name)}</div>
        <div class="text-xs text-muted font-mono">${escapeHtml(r.hospital_id)}</div>
      </td>
      <td><span class="badge badge-primary font-mono text-md font-bold">${escapeHtml(r.blood_group)}</span></td>
      <td>
        <div class="font-mono"><strong>${r.quantity}</strong> bags</div>
        <div class="text-xs text-muted">Issued: ${r.approved_quantity || 0} | Needed: <strong class="text-danger">${r.remaining_quantity ?? (r.quantity - (r.approved_quantity || 0))}</strong></div>
      </td>
      <td>${urgencyBadge}</td>
      <td>${timeRemainingHtml}</td>
      <td>${statusBadge}</td>
      <td>
        ${isPending ? `
          <button class="btn btn-primary btn-sm" onclick="openProcessModal('${r.request_id}')">
            <i class="fa-solid fa-bolt"></i> Process FEFO
          </button>
        ` : `
          <span class="text-xs text-muted font-medium"><i class="fa-solid fa-check"></i> Finalized</span>
        `}
      </td>
    </tr>
  `;
}

// 4. FEFO Process Modal
async function openProcessModal(requestId) {
  const reqRes = await API.get('/api/requests');
  const req = (reqRes.requests || []).find(r => r.request_id === requestId);
  if (!req) {
    showToast('Error', 'Could not locate request details.', 'error');
    return;
  }
  activeProcessRequest = req;

  document.getElementById('modal-process-req-id').innerText = req.request_id;
  document.getElementById('modal-process-hospital').innerText = req.hospital_name;
  document.getElementById('modal-process-group').innerText = req.blood_group;
  document.getElementById('modal-process-requested-qty').innerText = `${req.quantity} unit(s)`;
  
  const remaining = req.remaining_quantity ?? (req.quantity - (req.approved_quantity || 0));
  document.getElementById('modal-process-remaining-qty').innerText = `${remaining} unit(s)`;
  document.getElementById('modal-process-urgency').innerHTML = getBadgeHTML(req.emergency_level);

  // Partial input default
  const partialInput = document.getElementById('modal-process-partial-qty');
  if (partialInput) {
    partialInput.max = remaining;
    partialInput.value = remaining;
  }

  // Fetch available bags preview sorted by FEFO
  const bagsRes = await API.get(`/api/stock/bags?blood_group=${encodeURIComponent(req.blood_group)}&status=Available`);
  const availBags = bagsRes.bags || [];
  document.getElementById('modal-process-stock-count').innerText = `${availBags.length} Available`;

  const previewContainer = document.getElementById('modal-fifo-bags-preview');
  if (previewContainer) {
    if (availBags.length === 0) {
      previewContainer.innerHTML = `<div class="info-inset-box text-danger text-sm"><i class="fa-solid fa-triangle-exclamation"></i> No usable blood bags of type ${escapeHtml(req.blood_group)} currently available in stock.</div>`;
    } else {
      const candidateList = availBags.slice(0, remaining).map(b => `
        <div style="background:#ffffff; border:1px solid var(--border-color); border-radius:6px; padding:6px 10px; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center; font-size:0.8rem;">
          <span class="font-mono font-bold text-danger"><i class="fa-solid fa-droplet"></i> ${escapeHtml(b.bag_id)}</span>
          <span class="text-xs text-muted">Expires: <strong>${formatDate(b.expiry_date)}</strong> (${b.days_until_expiry}d left)</span>
          <span class="badge badge-success text-xs"><i class="fa-solid fa-check"></i> FEFO Priority #1</span>
        </div>
      `).join('');
      previewContainer.innerHTML = `
        <div class="info-inset-box">
          <div class="text-xs font-bold text-muted mb-1"><i class="fa-solid fa-arrow-down-short-wide"></i> FEFO Earliest-Expiry Bag Allocation Preview:</div>
          ${candidateList}
        </div>
      `;
    }
  }

  document.getElementById('process-request-modal').classList.add('active');
}

function closeProcessModal() {
  document.getElementById('process-request-modal').classList.remove('active');
  activeProcessRequest = null;
}

async function submitProcessDecision(decision) {
  if (!activeProcessRequest) return;
  const requestId = activeProcessRequest.request_id;
  const remarks = document.getElementById('modal-process-remarks')?.value?.trim();
  const partialQty = document.getElementById('modal-process-partial-qty')?.value;

  const payload = {
    decision: decision,
    remarks: remarks,
    approved_qty: decision === 'PARTIAL_APPROVE' ? parseInt(partialQty, 10) : undefined
  };

  const res = await API.post(`/api/requests/${requestId}/process`, payload);
  if (res.success) {
    showToast('Success', res.message, 'success');
    closeProcessModal();
    loadDashboardStats();
    loadStockSummary();
    loadBloodRequests();
    loadInvoicesList();
  } else {
    showToast('Processing Error', res.message, 'error');
  }
}

// 5. Blood Bags & Traceability
async function loadBloodBags() {
  const bg = document.getElementById('filter-bag-group')?.value || 'ALL';
  const status = document.getElementById('filter-bag-status')?.value || 'Available';
  const search = document.getElementById('search-bags')?.value || '';

  const res = await API.get(`/api/stock/bags?blood_group=${bg}&status=${status}&search=${encodeURIComponent(search)}`);
  if (!res.success) return;

  const tbody = document.getElementById('bloodbags-table-body');
  if (!tbody) return;

  const bags = res.bags || [];
  if (bags.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted" style="padding:2rem;">No blood bags matching criteria.</td></tr>`;
    return;
  }

  tbody.innerHTML = bags.map(b => `
    <tr>
      <td>
        <a href="javascript:void(0)" onclick="openBagDetailModal('${b.bag_id}')" class="font-mono font-bold text-danger">
          <i class="fa-solid fa-barcode"></i> ${escapeHtml(b.bag_id)}
        </a>
      </td>
      <td><span class="badge badge-primary font-mono font-bold">${escapeHtml(b.blood_group)}</span></td>
      <td>
        <div>${escapeHtml(b.donor_name || 'Anonymous')}</div>
        <div class="text-xs text-muted font-mono">${escapeHtml(b.donor_id || '-')}</div>
      </td>
      <td class="font-mono text-xs">${formatDate(b.collection_date)}</td>
      <td class="font-mono text-xs">
        ${formatDate(b.expiry_date)}
        <div class="text-xs ${b.is_critical_expiry ? 'text-danger font-bold' : 'text-muted'}">(${b.days_until_expiry ?? 0} days left)</div>
      </td>
      <td class="text-xs">${escapeHtml(b.storage_location || 'Cold Room A')}</td>
      <td class="font-mono text-xs font-bold">₹${Number(b.selling_price || 2500).toLocaleString('en-IN')}</td>
      <td>${getBadgeHTML(b.status)}</td>
    </tr>
  `).join('');
}

// Bag Traceability Modal
async function openBagDetailModal(bagId) {
  const res = await API.get(`/api/stock/${bagId}/timeline`);
  if (!res.success || !res.bag) {
    showToast('Error', 'Unable to retrieve bag history.', 'error');
    return;
  }

  const b = res.bag;
  const milestones = res.timeline || [];

  let modal = document.getElementById('bag-tracking-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'bag-tracking-modal';
    modal.className = 'modal-backdrop';
    document.body.appendChild(modal);
  }

  modal.innerHTML = `
    <div class="modal-dialog" style="max-width:650px;">
      <div class="modal-header">
        <h4><i class="fa-solid fa-qrcode text-danger"></i> Blood Bag Traceability: ${escapeHtml(b.bag_id)}</h4>
        <button class="btn-icon btn-secondary" onclick="document.getElementById('bag-tracking-modal').classList.remove('active')">&times;</button>
      </div>
      <div class="modal-body">
        <div style="display:flex; justify-content:space-between; align-items:center; background:#f8fafc; border:1px solid var(--border-color); border-radius:10px; padding:1rem; margin-bottom:1.25rem;">
          <div>
            <div class="text-xs text-muted font-bold">BLOOD UNIT</div>
            <h3 class="text-danger font-mono font-bold" style="margin:2px 0;">${escapeHtml(b.blood_group)} <span class="text-sm font-normal text-muted">(${b.volume_ml || 450} ml)</span></h3>
            <div class="text-xs text-muted">Bag ID: <strong class="font-mono">${escapeHtml(b.bag_id)}</strong></div>
          </div>
          <div style="text-align:right;">
            <div>${getBadgeHTML(b.status)}</div>
            <div class="text-xs text-muted font-mono mt-1">Expiry: <strong>${formatDate(b.expiry_date)}</strong></div>
          </div>
        </div>

        <h5 style="margin-bottom:0.75rem;"><i class="fa-solid fa-route text-primary"></i> Lifecycle Audit History</h5>
        <div style="border-left:2px solid var(--primary-border); padding-left:1.25rem; margin-left:0.5rem;">
          ${milestones.map(m => `
            <div style="position:relative; margin-bottom:1rem;">
              <div style="position:absolute; left:-1.65rem; top:2px; width:12px; height:12px; border-radius:50%; background:var(--primary); border:2px solid #fff;"></div>
              <div style="font-weight:700; font-size:0.875rem; color:var(--text-heading);">${escapeHtml(m.title)}</div>
              <div class="text-xs text-muted">${formatDateTime(m.timestamp)} &bull; By: <strong>${escapeHtml(m.actor)}</strong></div>
            </div>
          `).join('')}
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" onclick="window.print()"><i class="fa-solid fa-print"></i> Print Label</button>
        <button type="button" class="btn btn-primary" onclick="document.getElementById('bag-tracking-modal').classList.remove('active')">Close</button>
      </div>
    </div>
  `;
  modal.classList.add('active');
}

// 6. Donors Directory
async function loadDonorsList() {
  const search = document.getElementById('search-donors')?.value || '';
  const res = await API.get(`/api/donors?search=${encodeURIComponent(search)}`);
  if (!res.success) return;

  const tbody = document.getElementById('donors-table-body');
  if (!tbody) return;

  const donors = res.donors || [];
  if (donors.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted" style="padding:2rem;">No donors found.</td></tr>`;
    return;
  }

  tbody.innerHTML = donors.map(d => `
    <tr>
      <td class="font-mono font-bold">${escapeHtml(d.donor_id)}</td>
      <td>
        <div class="font-bold">${escapeHtml(d.name)}</div>
        <div class="text-xs text-muted">${escapeHtml(d.email || '-')}</div>
      </td>
      <td>${d.age} yrs / ${escapeHtml(d.gender || 'Male')}</td>
      <td><span class="badge badge-primary font-mono font-bold">${escapeHtml(d.blood_group)}</span></td>
      <td>${d.weight} kg</td>
      <td class="font-mono text-xs">${escapeHtml(d.contact || '-')}</td>
      <td>
        ${d.current_eligible
          ? `<span class="badge badge-success"><i class="fa-solid fa-circle-check"></i> Eligible</span>`
          : `<span class="badge badge-danger" title="${escapeHtml((d.eligibility_reasons || []).join('; '))}"><i class="fa-solid fa-circle-xmark"></i> Ineligible</span>`
        }
      </td>
      <td class="text-xs font-mono">${formatDate(d.last_donation_date)}</td>
    </tr>
  `).join('');
}

// 7. Entities (Hospitals & Coordinators)
async function loadHospitalsList() {
  const res = await API.get('/api/hospitals');
  if (!res.success) return;

  const tbody = document.getElementById('hospitals-table-body');
  if (!tbody) return;

  const hosps = res.hospitals || [];
  tbody.innerHTML = hosps.map(h => `
    <tr>
      <td class="font-mono font-bold">${escapeHtml(h.hospital_id)}</td>
      <td class="font-bold">${escapeHtml(h.name)}</td>
      <td class="text-xs">${escapeHtml(h.email)}</td>
      <td class="font-mono text-xs">${escapeHtml(h.phone || '-')}</td>
      <td class="text-xs">${escapeHtml(h.address || '-')}</td>
      <td class="font-mono font-bold ${h.outstanding_balance > 0 ? 'text-danger' : 'text-success'}">
        ${formatCurrency(h.outstanding_balance)}
      </td>
    </tr>
  `).join('');
}

async function loadCoordinatorsList() {
  const res = await API.get('/api/coordinators');
  if (!res.success) return;

  const tbody = document.getElementById('coordinators-table-body');
  if (!tbody) return;

  const coords = res.coordinators || [];
  tbody.innerHTML = coords.map(c => `
    <tr>
      <td class="font-mono font-bold">${escapeHtml(c.coordinator_id)}</td>
      <td class="font-bold">${escapeHtml(c.name)}</td>
      <td class="text-xs">${escapeHtml(c.email)}</td>
      <td class="text-xs">${escapeHtml(c.branch || 'Main Center')}</td>
      <td class="font-mono text-xs">${escapeHtml(c.phone || '-')}</td>
      <td>
        ${c.status === 'PENDING_APPROVAL' ? `
          <button class="btn btn-sm btn-primary" onclick="approveCoordinator('${c.coordinator_id}')">
            <i class="fa-solid fa-user-check"></i> Approve Staff
          </button>
        ` : `
          <span class="badge badge-success"><i class="fa-solid fa-check"></i> Active Staff</span>
        `}
      </td>
    </tr>
  `).join('');
}

async function approveCoordinator(coordId) {
  const res = await API.post(`/api/coordinators/${coordId}/status`, { status: 'ACTIVE' });
  if (res.success) {
    showToast('Activated', res.message, 'success');
    loadCoordinatorsList();
  } else {
    showToast('Error', res.message, 'error');
  }
}

async function submitAddHospital(e) {
  e.preventDefault();
  const payload = {
    name: document.getElementById('hosp-name').value.trim(),
    email: document.getElementById('hosp-email').value.trim(),
    password: document.getElementById('hosp-password').value.trim(),
    phone: document.getElementById('hosp-phone').value.trim(),
    address: document.getElementById('hosp-address').value.trim(),
    initial_balance: parseFloat(document.getElementById('hosp-balance').value || 0)
  };

  const res = await API.post('/api/hospitals/add', payload);
  if (res.success) {
    showToast('Success', res.message, 'success');
    document.getElementById('add-hospital-form').reset();
    document.getElementById('add-hospital-modal').classList.remove('active');
    loadHospitalsList();
    loadDashboardStats();
  } else {
    showToast('Error', res.message, 'error');
  }
}

async function submitAddCoordinator(e) {
  e.preventDefault();
  const payload = {
    name: document.getElementById('coord-name').value.trim(),
    email: document.getElementById('coord-email').value.trim(),
    password: document.getElementById('coord-password').value.trim(),
    branch: document.getElementById('coord-branch').value.trim(),
    phone: document.getElementById('coord-phone').value.trim()
  };

  const res = await API.post('/api/coordinators/add', payload);
  if (res.success) {
    showToast('Success', res.message, 'success');
    document.getElementById('add-coordinator-form').reset();
    document.getElementById('add-coordinator-modal').classList.remove('active');
    loadCoordinatorsList();
  } else {
    showToast('Error', res.message, 'error');
  }
}

// 8. Invoices Ledger
async function loadInvoicesList() {
  const res = await API.get('/api/invoices');
  if (!res.success) return;

  const tbody = document.getElementById('invoices-table-body');
  if (!tbody) return;

  const invoices = res.invoices || [];
  if (invoices.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" class="text-center text-muted" style="padding:2rem;">No invoices generated yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = invoices.map(i => `
    <tr>
      <td class="font-mono font-bold">${escapeHtml(i.invoice_number)}</td>
      <td class="font-bold">${escapeHtml(i.hospital_name)}</td>
      <td class="font-mono text-xs">${escapeHtml(i.request_id)}</td>
      <td><span class="badge badge-primary font-mono">${escapeHtml(i.blood_group)}</span></td>
      <td class="font-mono">${i.quantity}</td>
      <td class="font-mono text-xs">₹${Number(i.subtotal).toLocaleString('en-IN')}</td>
      <td class="font-mono text-xs">₹${Number(i.tax_amount).toLocaleString('en-IN')}</td>
      <td class="font-mono font-bold text-gradient">${formatCurrency(i.total_amount)}</td>
      <td>${getBadgeHTML(i.status)}</td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="openInvoiceDetailModal('${i.invoice_number}')">
          <i class="fa-solid fa-eye"></i> View
        </button>
      </td>
    </tr>
  `).join('');
}

async function openInvoiceDetailModal(invNumber) {
  const res = await API.get(`/api/invoices/${invNumber}`);
  if (!res.success || !res.invoice) {
    showToast('Error', 'Unable to fetch invoice details.', 'error');
    return;
  }

  const i = res.invoice;
  const h = res.hospital || {};
  const bags = res.bags || [];

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

// 9. Activity Log & Reports
async function loadActivityAuditLog() {
  const res = await API.get('/api/reports/activity-log?limit=30');
  const tbody = document.getElementById('audit-activity-table-body');
  if (!tbody || !res.success) return;

  const logs = res.logs || [];
  if (logs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted" style="padding:2rem;">No system audit logs found.</td></tr>`;
    return;
  }

  tbody.innerHTML = logs.map(l => `
    <tr>
      <td class="font-mono text-xs">${formatDateTime(l.timestamp)}</td>
      <td class="font-bold text-xs">${escapeHtml(l.actor_name)} <span class="text-muted">(${escapeHtml(l.actor_role)})</span></td>
      <td><span class="badge badge-primary text-xs">${escapeHtml(l.action)}</span></td>
      <td class="text-sm">${escapeHtml(l.description)}</td>
      <td class="font-mono text-xs text-muted">${escapeHtml(l.target_id || '-')}</td>
    </tr>
  `).join('');
}

function triggerTextExport() {
  window.open('/api/reports/export/text', '_blank');
}

function triggerCsvExport(target) {
  window.open(`/api/reports/export/csv/${target}`, '_blank');
}
