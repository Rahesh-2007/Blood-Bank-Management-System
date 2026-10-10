/**
 * Blood Bank Staff Dashboard Controller
 */

let currentSection = 'register-donor';
let activeScreeningBag = null;

document.addEventListener('DOMContentLoaded', async () => {
  // Check auth
  const authRes = await API.getCurrentUser();
  if (!authRes.authenticated || authRes.user.role !== 'COORDINATOR') {
    window.location.href = '/';
    return;
  }

  document.getElementById('coord-user-name').innerText = authRes.user.name || 'Blood Bank Staff';
  const branchEl = document.getElementById('coord-branch-name');
  if (branchEl) branchEl.innerText = authRes.user.branch || authRes.user.blood_bank_branch || 'Main Blood Bank Branch';

  setupSidebarNav();
  setupLiveEligibilityChecker();
  setupRegisterDonorForm();
  setupRecordDonationForm();
  loadDonorsForSelect();
  loadDonorsTable();
  loadTodayDonations();
  loadCoordinatorInventory();
  loadPendingScreeningBags();
});

function setupSidebarNav() {
  const items = document.querySelectorAll('.sidebar-nav .nav-item');
  items.forEach(item => {
    item.addEventListener('click', () => {
      items.forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      const target = item.dataset.section;
      showCoordinatorSection(target);
    });
  });
}

function showCoordinatorSection(sectionId) {
  currentSection = sectionId;
  document.querySelectorAll('.coord-section').forEach(sec => sec.style.display = 'none');
  const targetSec = document.getElementById(`section-${sectionId}`);
  if (targetSec) targetSec.style.display = 'block';

  // Highlight sidebar item
  document.querySelectorAll('.sidebar-nav .nav-item').forEach(i => {
    i.classList.toggle('active', i.dataset.section === sectionId);
  });

  if (sectionId === 'donors-list') {
    loadDonorsTable();
  } else if (sectionId === 'record-donation') {
    loadDonorsForSelect();
  } else if (sectionId === 'today-donations') {
    loadTodayDonations();
  } else if (sectionId === 'screening') {
    loadPendingScreeningBags();
  } else if (sectionId === 'inventory') {
    loadCoordinatorInventory();
  } else if (sectionId === 'profile') {
    loadUserProfile();
  }
}

// 1. Live Clinical Eligibility Checker
function setupLiveEligibilityChecker() {
  const ageInput = document.getElementById('reg-age');
  const weightInput = document.getElementById('reg-weight');
  const healthCheck = document.getElementById('reg-health-issue');
  const lastDonationInput = document.getElementById('reg-last-donation');
  const feedbackBox = document.getElementById('live-eligibility-box');

  const checkEligibilityLive = async () => {
    const age = parseInt(ageInput?.value || 0, 10);
    const weight = parseFloat(weightInput?.value || 0);
    const hasHealthIssue = healthCheck?.checked || false;
    const lastDonation = lastDonationInput?.value || null;

    if (!age && !weight) {
      if (feedbackBox) feedbackBox.innerHTML = '';
      return;
    }

    const res = await API.post('/api/donors/check-eligibility', {
      age,
      weight,
      has_health_issues: hasHealthIssue,
      last_donation_date: lastDonation
    });

    if (res.success && feedbackBox) {
      if (res.is_eligible) {
        feedbackBox.innerHTML = `
          <div class="badge badge-success" style="width:100%; padding:0.75rem; border-radius:8px; font-size:0.85rem; justify-content:flex-start;">
            <i class="fa-solid fa-circle-check"></i> &nbsp;<strong>ELIGIBLE:</strong> Donor meets all criteria for blood collection (Age 18-60, Weight ≥ 45kg).
          </div>
        `;
      } else {
        feedbackBox.innerHTML = `
          <div class="badge badge-danger" style="width:100%; padding:0.75rem; border-radius:8px; font-size:0.85rem; justify-content:flex-start; flex-direction:column; align-items:flex-start; gap:4px;">
            <div><i class="fa-solid fa-circle-xmark"></i> <strong>INELIGIBLE FOR DONATION:</strong></div>
            <ul style="margin-left:1.25rem; font-weight:normal; font-size:0.8rem; text-transform:none;">
              ${(res.reasons || []).map(r => `<li>${escapeHtml(r)}</li>`).join('')}
            </ul>
          </div>
        `;
      }
    }
  };

  if (ageInput) ageInput.addEventListener('input', checkEligibilityLive);
  if (weightInput) weightInput.addEventListener('input', checkEligibilityLive);
  if (healthCheck) healthCheck.addEventListener('change', checkEligibilityLive);
  if (lastDonationInput) lastDonationInput.addEventListener('change', checkEligibilityLive);
}

// 2. Register Donor Form
function setupRegisterDonorForm() {
  const form = document.getElementById('register-donor-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('reg-submit-btn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Registering...'; }

    const payload = {
      name: document.getElementById('reg-name').value.trim(),
      blood_group: document.getElementById('reg-blood-group').value,
      age: parseInt(document.getElementById('reg-age').value, 10),
      weight: parseFloat(document.getElementById('reg-weight').value),
      gender: document.getElementById('reg-gender').value,
      contact: document.getElementById('reg-contact').value.trim(),
      email: document.getElementById('reg-email').value.trim(),
      last_donation_date: document.getElementById('reg-last-donation').value || null,
      has_health_issues: document.getElementById('reg-health-issue').checked,
      health_notes: document.getElementById('reg-health-notes').value.trim()
    };

    const res = await API.post('/api/donors/register', payload);
    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-user-check"></i> Register Donor & Evaluate'; }

    if (res.success) {
      showToast('Registration Successful', res.message, 'success');
      form.reset();
      document.getElementById('live-eligibility-box').innerHTML = '';
      loadDonorsForSelect();
      loadDonorsTable();

      // Offer immediate flow to record donation if eligible
      if (res.donor && res.donor.eligible) {
        setTimeout(() => {
          showCoordinatorSection('record-donation');
          const sel = document.getElementById('donate-donor-select');
          if (sel) {
            sel.value = res.donor.donor_id;
            sel.dispatchEvent(new Event('change'));
          }
        }, 500);
      }
    } else {
      showToast('Registration Failed', res.message, 'error');
    }
  });
}

// 3. Record Donation Form
async function loadDonorsForSelect() {
  const res = await API.get('/api/donors');
  const sel = document.getElementById('donate-donor-select');
  if (!sel || !res.success) return;

  const donors = res.donors || [];
  sel.innerHTML = '<option value="">-- Choose Donor --</option>' + donors.map(d => {
    const elTag = d.current_eligible ? 'ELIGIBLE' : 'INELIGIBLE';
    return `<option value="${d.donor_id}" data-eligible="${d.current_eligible}">${d.donor_id} - ${escapeHtml(d.name)} (${d.blood_group}) [${elTag}]</option>`;
  }).join('');
}

function setupRecordDonationForm() {
  const sel = document.getElementById('donate-donor-select');
  const form = document.getElementById('record-donation-form');
  const submitBtn = document.getElementById('record-donation-btn');

  if (sel) {
    sel.addEventListener('change', async () => {
      const donorId = sel.value;
      const card = document.getElementById('donate-donor-info-card');
      if (!donorId) {
        if (card) card.style.display = 'none';
        if (submitBtn) submitBtn.disabled = true;
        return;
      }

      const res = await API.get(`/api/donors/${donorId}`);
      if (!res.success || !res.donor) return;

      const d = res.donor;
      if (card) {
        card.style.display = 'block';
        document.getElementById('card-donor-name').innerText = d.name;
        document.getElementById('card-donor-group').innerText = d.blood_group;
        document.getElementById('card-donor-age').innerText = `${d.age} yrs`;
        document.getElementById('card-donor-weight').innerText = `${d.weight} kg`;
        document.getElementById('card-donor-last-donate').innerText = formatDate(d.last_donation_date);

        const statusEl = document.getElementById('card-donor-status');
        if (d.current_eligible) {
          statusEl.innerHTML = `<span class="badge badge-success"><i class="fa-solid fa-circle-check"></i> Eligible</span>`;
          if (submitBtn) submitBtn.disabled = false;
        } else {
          statusEl.innerHTML = `<span class="badge badge-danger"><i class="fa-solid fa-circle-xmark"></i> Ineligible</span>`;
          if (submitBtn) submitBtn.disabled = true;
        }
      }
    });
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!submitBtn || submitBtn.disabled) return;

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing Collection...';

      const payload = {
        donor_id: sel.value,
        volume_ml: parseInt(document.getElementById('donate-volume').value, 10),
        storage_location: document.getElementById('donate-location').value.trim()
      };

      const res = await API.post('/api/donations/record', payload);
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fa-solid fa-droplet"></i> Complete Donation & Create Blood Bag';

      if (res.success) {
        showToast('Donation Recorded', res.message, 'success');
        form.reset();
        document.getElementById('donate-donor-info-card').style.display = 'none';
        loadTodayDonations();
        loadPendingScreeningBags();
        loadCoordinatorInventory();
        loadDonorsForSelect();
      } else {
        showToast('Error', res.message, 'error');
      }
    });
  }
}

// 4. Lab Screening Workflow
async function loadPendingScreeningBags() {
  const res = await API.get('/api/stock/bags?status=Pending Screening');
  const tbody = document.getElementById('screening-table-body');
  if (!tbody || !res.success) return;

  const bags = res.bags || [];
  if (bags.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted" style="padding:2rem;"><i class="fa-solid fa-circle-check text-success"></i> All collected blood units have been screened and cleared!</td></tr>`;
    return;
  }

  tbody.innerHTML = bags.map(b => `
    <tr>
      <td class="font-mono font-bold text-danger">${escapeHtml(b.bag_id)}</td>
      <td><span class="badge badge-primary font-mono font-bold">${escapeHtml(b.blood_group)}</span></td>
      <td>
        <div class="font-bold">${escapeHtml(b.donor_name)}</div>
        <div class="text-xs text-muted font-mono">${escapeHtml(b.donor_id)}</div>
      </td>
      <td class="font-mono text-xs">${formatDateTime(b.collection_date)}</td>
      <td class="text-xs">${escapeHtml(b.storage_location || 'Quarantine')}</td>
      <td><span class="badge badge-warning"><i class="fa-solid fa-microscope"></i> Pending Tests</span></td>
      <td>
        <button class="btn btn-primary btn-sm" onclick="openScreeningModal('${b.bag_id}')">
          <i class="fa-solid fa-vial-virus"></i> Record Lab Screening
        </button>
      </td>
    </tr>
  `).join('');
}

function openScreeningModal(bagId) {
  activeScreeningBag = bagId;
  const modal = document.getElementById('screening-modal');
  if (modal) {
    document.getElementById('screen-modal-bag-id').innerText = bagId;
    modal.classList.add('active');
  }
}

function closeScreeningModal() {
  const modal = document.getElementById('screening-modal');
  if (modal) modal.classList.remove('active');
  activeScreeningBag = null;
}

async function submitScreeningDecision(result) {
  if (!activeScreeningBag) return;

  const payload = {
    result: result,
    hiv_test: document.getElementById('screen-hiv')?.value || 'NEGATIVE',
    hbv_test: document.getElementById('screen-hbv')?.value || 'NEGATIVE',
    hcv_test: document.getElementById('screen-hcv')?.value || 'NEGATIVE',
    syphilis_test: document.getElementById('screen-syphilis')?.value || 'NEGATIVE',
    malaria_test: document.getElementById('screen-malaria')?.value || 'NEGATIVE',
    notes: document.getElementById('screen-notes')?.value?.trim() || ''
  };

  const res = await API.post(`/api/donations/screen/${activeScreeningBag}`, payload);
  if (res.success) {
    showToast('Screening Logged', res.message, 'success');
    closeScreeningModal();
    loadPendingScreeningBags();
    loadCoordinatorInventory();
  } else {
    showToast('Screening Error', res.message, 'error');
  }
}

// 5. Donors Table Directory & Profile Editing
async function loadDonorsTable() {
  const group = document.getElementById('coord-filter-donor-group')?.value || 'ALL';
  const search = document.getElementById('coord-search-donor')?.value || '';

  const res = await API.get(`/api/donors?blood_group=${group}&search=${encodeURIComponent(search)}`);
  const tbody = document.getElementById('coord-donors-table-body');
  if (!tbody || !res.success) return;

  const donors = res.donors || [];
  if (donors.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted" style="padding:2rem;">No donors found.</td></tr>`;
    return;
  }

  tbody.innerHTML = donors.map(d => `
    <tr>
      <td class="font-mono font-bold">${escapeHtml(d.donor_id)}</td>
      <td class="font-bold">${escapeHtml(d.name)}</td>
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
      <td class="font-mono text-xs">${formatDate(d.last_donation_date)}</td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="openDonorEditModal('${d.donor_id}')">
          <i class="fa-solid fa-user-pen"></i> Edit / Profile
        </button>
      </td>
    </tr>
  `).join('');
}

async function openDonorEditModal(donorId) {
  const res = await API.get(`/api/donors/${donorId}`);
  if (!res.success || !res.donor) {
    showToast('Error', 'Unable to retrieve donor profile.', 'error');
    return;
  }

  const d = res.donor;
  const history = res.donations || [];

  let modal = document.getElementById('donor-profile-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'donor-profile-modal';
    modal.className = 'modal-backdrop';
    document.body.appendChild(modal);
  }

  modal.innerHTML = `
    <div class="modal-dialog" style="max-width:680px;">
      <div class="modal-header">
        <h4><i class="fa-solid fa-address-card text-danger"></i> Donor Profile: ${escapeHtml(d.name)}</h4>
        <button class="btn-icon btn-secondary" onclick="document.getElementById('donor-profile-modal').classList.remove('active')">&times;</button>
      </div>
      <div class="modal-body">
        <div style="background:#f8fafc; border:1px solid var(--border-color); border-radius:10px; padding:1rem; margin-bottom:1.25rem; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <span class="text-xs text-muted font-bold font-mono">ID: ${escapeHtml(d.donor_id)}</span>
            <h3 style="margin:2px 0;">${escapeHtml(d.name)} <span class="badge badge-primary font-mono text-md">${escapeHtml(d.blood_group)}</span></h3>
            <div class="text-xs text-muted">${d.age} yrs &bull; ${d.weight} kg &bull; ${escapeHtml(d.gender || 'Male')}</div>
          </div>
          <div style="text-align:right;">
            <div>${d.current_eligible ? '<span class="badge badge-success"><i class="fa-solid fa-circle-check"></i> Eligible</span>' : '<span class="badge badge-danger"><i class="fa-solid fa-circle-xmark"></i> Ineligible</span>'}</div>
            <div class="text-xs text-muted mt-1">Next Eligible: <strong>${d.next_eligible_date || 'Immediate'}</strong></div>
          </div>
        </div>

        <form id="edit-donor-form" onsubmit="submitDonorUpdate(event, '${d.donor_id}')">
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1rem;">
            <div class="form-group">
              <label class="form-label">Full Name</label>
              <input type="text" id="edit-d-name" class="form-control" value="${escapeHtml(d.name)}" required>
            </div>
            <div class="form-group">
              <label class="form-label">Contact Phone</label>
              <input type="text" id="edit-d-contact" class="form-control" value="${escapeHtml(d.contact || '')}">
            </div>
            <div class="form-group">
              <label class="form-label">Email</label>
              <input type="email" id="edit-d-email" class="form-control" value="${escapeHtml(d.email || '')}">
            </div>
            <div class="form-group">
              <label class="form-label">Weight (kg)</label>
              <input type="number" step="0.5" id="edit-d-weight" class="form-control" value="${d.weight}">
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Health Notes</label>
            <input type="text" id="edit-d-notes" class="form-control" value="${escapeHtml(d.health_notes || '')}" placeholder="Medical remarks...">
          </div>

          <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border-color); padding-top:1rem;">
            <button type="button" class="btn ${d.status === 'Active' ? 'btn-outline-danger' : 'btn-success'} btn-sm" onclick="toggleDonorStatus('${d.donor_id}', '${d.status === 'Active' ? 'Deactivated' : 'Active'}')">
              ${d.status === 'Active' ? '<i class="fa-solid fa-user-slash"></i> Deactivate Donor' : '<i class="fa-solid fa-user-check"></i> Reactivate Donor'}
            </button>
            <button type="submit" class="btn btn-primary btn-sm"><i class="fa-solid fa-floppy-disk"></i> Save Changes</button>
          </div>
        </form>

        <h5 style="margin:1.5rem 0 0.75rem 0;"><i class="fa-solid fa-clock-rotate-left text-danger"></i> Past Donation History (${history.length})</h5>
        <div class="table-responsive">
          <table class="custom-table text-xs">
            <thead>
              <tr><th>Bag ID</th><th>Collected</th><th>Expiry</th><th>Volume</th><th>Status</th></tr>
            </thead>
            <tbody>
              ${history.length === 0 ? '<tr><td colspan="5" class="text-center text-muted">No donations recorded yet.</td></tr>' : history.map(h => `
                <tr>
                  <td class="font-mono font-bold">${escapeHtml(h.bag_id)}</td>
                  <td>${formatDate(h.collection_date)}</td>
                  <td>${formatDate(h.expiry_date)}</td>
                  <td>${h.volume_ml} ml</td>
                  <td>${getBadgeHTML(h.status)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" onclick="document.getElementById('donor-profile-modal').classList.remove('active')">Close</button>
      </div>
    </div>
  `;
  modal.classList.add('active');
}

async function submitDonorUpdate(e, donorId) {
  e.preventDefault();
  const payload = {
    name: document.getElementById('edit-d-name').value.trim(),
    contact: document.getElementById('edit-d-contact').value.trim(),
    email: document.getElementById('edit-d-email').value.trim(),
    weight: parseFloat(document.getElementById('edit-d-weight').value),
    health_notes: document.getElementById('edit-d-notes').value.trim()
  };

  const res = await API.put(`/api/donors/${donorId}`, payload);
  if (res.success) {
    showToast('Profile Updated', res.message, 'success');
    document.getElementById('donor-profile-modal').classList.remove('active');
    loadDonorsTable();
  } else {
    showToast('Error', res.message, 'error');
  }
}

async function toggleDonorStatus(donorId, newStatus) {
  const res = await API.post(`/api/donors/${donorId}/status`, { status: newStatus });
  if (res.success) {
    showToast('Status Changed', res.message, 'success');
    document.getElementById('donor-profile-modal').classList.remove('active');
    loadDonorsTable();
  } else {
    showToast('Error', res.message, 'error');
  }
}

// 6. Today's Donations & Inventory View
async function loadTodayDonations() {
  const res = await API.get('/api/donations/history?today=true');
  const tbody = document.getElementById('today-donations-table-body');
  if (!tbody || !res.success) return;

  const donations = res.donations || [];
  if (donations.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted" style="padding:2rem;">No blood donations recorded today yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = donations.map(d => `
    <tr>
      <td class="font-mono font-bold text-danger">${escapeHtml(d.bag_id)}</td>
      <td class="font-bold">${escapeHtml(d.donor_name)}</td>
      <td><span class="badge badge-primary font-mono font-bold">${escapeHtml(d.blood_group)}</span></td>
      <td class="font-mono">${d.volume_ml} ml</td>
      <td class="text-xs">${escapeHtml(d.storage_location || 'Cold Room A')}</td>
      <td class="font-mono text-xs">${formatDateTime(d.collection_date)}</td>
      <td>${getBadgeHTML(d.status)}</td>
    </tr>
  `).join('');
}

async function loadCoordinatorInventory() {
  const res = await API.get('/api/stock/summary');
  const container = document.getElementById('coord-stock-cards');
  if (!container || !res.success) return;

  container.innerHTML = (res.groups || []).map(g => `
    <div class="stock-card">
      <div class="blood-type">${escapeHtml(g.blood_group)}</div>
      <div class="stock-condition-group">
        ${g.is_out_of_stock ? '<span class="stock-condition-item out-of-stock">0 Bags</span>' : `<span class="stock-condition-item good">${g.available_count} Available</span>`}
      </div>
      <div class="stock-price">₹${Number(g.price_per_unit).toLocaleString('en-IN')}/bag</div>
    </div>
  `).join('');
}
