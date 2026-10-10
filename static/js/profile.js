/**
 * Blood Bank Management System - Common Profile Controller
 * Serves Super Admin, Coordinator, and Hospital Portals
 */

async function loadUserProfile() {
  const res = await API.get('/api/profile/me');
  if (!res.success || !res.profile) {
    showToast('Error', 'Unable to load user profile.', 'error');
    return;
  }

  const p = res.profile;
  const stats = res.stats || {};
  const recentLogs = res.recent_activity || [];

  // Update Top Profile Header
  const nameEl = document.getElementById('profile-display-name');
  const roleEl = document.getElementById('profile-display-role');
  const idEl = document.getElementById('profile-display-id');
  const statusEl = document.getElementById('profile-display-status');
  const avatarEl = document.getElementById('profile-avatar-initials');

  if (nameEl) nameEl.innerText = p.name || 'User Profile';
  if (roleEl) roleEl.innerText = p.role_display || p.role;
  if (idEl) idEl.innerText = p.account_id || p.hospital_id || p.coordinator_id || 'ID-001';
  if (statusEl) {
    const isAct = (p.status === 'ACTIVE' || p.status === 'Active');
    statusEl.className = isAct ? 'badge badge-success' : 'badge badge-warning';
    statusEl.innerHTML = isAct ? '<i class="fa-solid fa-circle-check"></i> Active & Verified' : '<i class="fa-solid fa-clock"></i> Pending Review';
  }
  if (avatarEl) {
    const initials = (p.name || 'U').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    avatarEl.innerText = initials;
  }

  // Populate Edit Form Fields
  const nameInput = document.getElementById('prof-input-name');
  const emailInput = document.getElementById('prof-input-email');
  const phoneInput = document.getElementById('prof-input-phone');
  const idInput = document.getElementById('prof-input-id');
  const roleInput = document.getElementById('prof-input-role');
  const joinedInput = document.getElementById('prof-input-joined');

  if (nameInput) nameInput.value = p.name || '';
  if (emailInput) emailInput.value = p.email || '';
  if (phoneInput) phoneInput.value = p.phone || '';
  if (idInput) idInput.value = p.account_id || '';
  if (roleInput) roleInput.value = p.role_display || p.role || '';
  if (joinedInput) joinedInput.value = formatDate(p.created_at);

  // Role-specific fields
  if (p.role === 'ADMIN') {
    const desigInput = document.getElementById('prof-input-designation');
    const deptInput = document.getElementById('prof-input-department');
    if (desigInput) desigInput.value = p.designation || '';
    if (deptInput) deptInput.value = p.department || '';
  } else if (p.role === 'COORDINATOR') {
    const branchInput = document.getElementById('prof-input-branch');
    const desigInput = document.getElementById('prof-input-designation');
    if (branchInput) branchInput.value = p.branch || '';
    if (desigInput) desigInput.value = p.designation || '';
  } else if (p.role === 'HOSPITAL') {
    const addrInput = document.getElementById('prof-input-address');
    const contactInput = document.getElementById('prof-input-contact-person');
    const regInput = document.getElementById('prof-input-reg-number');
    const billingInput = document.getElementById('prof-input-billing-address');
    if (addrInput) addrInput.value = p.address || '';
    if (contactInput) contactInput.value = p.contact_person || '';
    if (regInput) regInput.value = p.reg_number || '';
    if (billingInput) billingInput.value = p.billing_address || p.address || '';
  }

  // Populate Activity Log Table
  renderProfileActivity(recentLogs);
}

function renderProfileActivity(logs) {
  const tbody = document.getElementById('profile-activity-table-body');
  if (!tbody) return;

  if (!logs || logs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted" style="padding:2rem;">No recent audit activity recorded yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = logs.map(l => `
    <tr>
      <td class="font-mono text-xs" style="white-space:nowrap;">${formatDateTime(l.timestamp)}</td>
      <td><span class="badge badge-primary text-xs">${escapeHtml(l.action)}</span></td>
      <td>${escapeHtml(l.description)}</td>
      <td class="font-mono text-xs text-muted">${escapeHtml(l.target_id || '-')}</td>
    </tr>
  `).join('');
}

async function handleProfileUpdate(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-save-profile');
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...'; }

  const payload = {
    name: document.getElementById('prof-input-name')?.value?.trim(),
    phone: document.getElementById('prof-input-phone')?.value?.trim(),
    designation: document.getElementById('prof-input-designation')?.value?.trim(),
    department: document.getElementById('prof-input-department')?.value?.trim(),
    address: document.getElementById('prof-input-address')?.value?.trim(),
    contact_person: document.getElementById('prof-input-contact-person')?.value?.trim(),
    billing_address: document.getElementById('prof-input-billing-address')?.value?.trim()
  };

  const res = await API.put('/api/profile/me', payload);
  if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Profile Changes'; }

  if (res.success) {
    showToast('Success', res.message, 'success');
    loadUserProfile();
  } else {
    showToast('Error', res.message, 'error');
  }
}

async function handlePasswordChange(e) {
  e.preventDefault();
  const current_password = document.getElementById('prof-curr-pass')?.value?.trim();
  const new_password = document.getElementById('prof-new-pass')?.value?.trim();
  const confirm_password = document.getElementById('prof-confirm-pass')?.value?.trim();

  if (new_password !== confirm_password) {
    showToast('Validation Error', 'New password and confirmation do not match.', 'warning');
    return;
  }

  const btn = document.getElementById('btn-save-password');
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Updating...'; }

  const res = await API.post('/api/profile/change-password', {
    current_password,
    new_password,
    confirm_password
  });

  if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-key"></i> Update Password'; }

  if (res.success) {
    showToast('Security Update', res.message, 'success');
    document.getElementById('form-change-password')?.reset();
  } else {
    showToast('Error', res.message, 'error');
  }
}

async function handleEmailChange(e) {
  e.preventDefault();
  const new_email = document.getElementById('prof-new-email')?.value?.trim();
  const password = document.getElementById('prof-email-pass')?.value?.trim();

  const btn = document.getElementById('btn-save-email');
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Updating...'; }

  const res = await API.post('/api/profile/change-email', {
    new_email,
    password
  });

  if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-envelope"></i> Change Email Address'; }

  if (res.success) {
    showToast('Email Updated', res.message, 'success');
    document.getElementById('form-change-email')?.reset();
    loadUserProfile();
  } else {
    showToast('Error', res.message, 'error');
  }
}

async function handleNotificationSave(e) {
  e.preventDefault();
  const payload = {
    urgent_alerts: document.getElementById('notif-urgent')?.checked ?? true,
    stock_expiry_alerts: document.getElementById('notif-expiry')?.checked ?? true,
    invoice_billing_alerts: document.getElementById('notif-invoice')?.checked ?? true,
    email_digest: document.getElementById('notif-digest')?.checked ?? false
  };

  const res = await API.post('/api/profile/notifications', payload);
  if (res.success) {
    showToast('Preferences Saved', res.message, 'success');
  } else {
    showToast('Error', res.message, 'error');
  }
}

function switchProfileTab(tabName) {
  document.querySelectorAll('.profile-subtab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.profile-tab-content').forEach(c => c.style.display = 'none');

  const btn = document.querySelector(`.profile-subtab[data-tab="${tabName}"]`);
  const content = document.getElementById(`profile-tab-${tabName}`);
  if (btn) btn.classList.add('active');
  if (content) content.style.display = 'block';
}
