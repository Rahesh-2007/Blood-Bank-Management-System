/**
 * Signup Controller - Direct Registration & Authentication
 */

let currentSignupRole = 'HOSPITAL';

document.addEventListener('DOMContentLoaded', () => {
  setupSignupRoleTabs();
  setupPasswordStrengthMeter();
  setupSignupForm();
});

function setupSignupRoleTabs() {
  const tabs = document.querySelectorAll('.auth-tab-btn');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      currentSignupRole = tab.dataset.role;
      renderSignupFields(currentSignupRole);
    });
  });
  renderSignupFields(currentSignupRole);
}

function renderSignupFields(role) {
  const container = document.getElementById('dynamic-signup-fields');
  if (!container) return;

  if (role === 'HOSPITAL') {
    container.innerHTML = `
      <div class="form-group">
        <label class="form-label"><i class="fa-solid fa-hospital"></i> Hospital Official Name</label>
        <input type="text" id="signup-name" class="form-control" placeholder="e.g. Apollo Memorial Hospital" required>
      </div>
      <div class="form-group">
        <label class="form-label"><i class="fa-solid fa-envelope"></i> Hospital Registered Email</label>
        <input type="email" id="signup-email" class="form-control" placeholder="contact@hospital.org" required>
      </div>
      <div class="form-row" style="display:grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
        <div class="form-group">
          <label class="form-label"><i class="fa-solid fa-phone"></i> Emergency Phone</label>
          <input type="tel" id="signup-phone" class="form-control" placeholder="+91 98765 00000" required>
        </div>
        <div class="form-group">
          <label class="form-label"><i class="fa-solid fa-location-dot"></i> City / Sector</label>
          <input type="text" id="signup-address" class="form-control" placeholder="Central Healthcare District" required>
        </div>
      </div>
    `;
  } else if (role === 'COORDINATOR') {
    container.innerHTML = `
      <div class="form-group">
        <label class="form-label"><i class="fa-solid fa-user-doctor"></i> Full Name (Blood Bank Staff)</label>
        <input type="text" id="signup-name" class="form-control" placeholder="Dr. Jane Smith" required>
      </div>
      <div class="form-group">
        <label class="form-label"><i class="fa-solid fa-envelope"></i> Staff Email Address</label>
        <input type="email" id="signup-email" class="form-control" placeholder="jane.smith@bloodbank.org" required>
      </div>
      <div class="form-row" style="display:grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
        <div class="form-group">
          <label class="form-label"><i class="fa-solid fa-phone"></i> Contact Phone</label>
          <input type="tel" id="signup-phone" class="form-control" placeholder="+91 98765 11111" required>
        </div>
        <div class="form-group">
          <label class="form-label"><i class="fa-solid fa-building"></i> Branch / Center</label>
          <input type="text" id="signup-branch" class="form-control" placeholder="Central Blood Bank" required>
        </div>
      </div>
    `;
  }
}

function setupPasswordStrengthMeter() {
  const pwInput = document.getElementById('signup-password');
  const bar = document.getElementById('password-strength-bar');
  if (!pwInput || !bar) return;

  pwInput.addEventListener('input', () => {
    const val = pwInput.value;
    let score = 0;
    if (val.length >= 6) score += 25;
    if (val.length >= 9) score += 25;
    if (/[A-Z]/.test(val) && /[a-z]/.test(val)) score += 25;
    if (/[0-9]/.test(val) || /[^A-Za-z0-9]/.test(val)) score += 25;

    bar.style.width = `${score}%`;
    if (score <= 25) {
      bar.style.backgroundColor = '#ef4444';
    } else if (score <= 50) {
      bar.style.backgroundColor = '#f97316';
    } else if (score <= 75) {
      bar.style.backgroundColor = '#eab308';
    } else {
      bar.style.backgroundColor = '#10b981';
    }
  });
}

function setupSignupForm() {
  const form = document.getElementById('signup-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('signup-submit-btn');
    const originalText = btn.innerHTML;

    const name = document.getElementById('signup-name')?.value.trim();
    const email = document.getElementById('signup-email')?.value.trim();
    const phone = document.getElementById('signup-phone')?.value.trim();
    const password = document.getElementById('signup-password')?.value.trim();
    const confirmPassword = document.getElementById('signup-confirm-password')?.value.trim();

    if (password !== confirmPassword) {
      showToast('Validation Error', 'Passwords do not match. Please re-enter.', 'error');
      return;
    }

    if (password.length < 6) {
      showToast('Validation Error', 'Password must be at least 6 characters.', 'error');
      return;
    }

    const payload = {
      role: currentSignupRole,
      name,
      email,
      phone,
      password,
      confirm_password: confirmPassword
    };

    if (currentSignupRole === 'HOSPITAL') {
      payload.address = document.getElementById('signup-address')?.value.trim();
    } else if (currentSignupRole === 'COORDINATOR') {
      payload.branch = document.getElementById('signup-branch')?.value.trim();
    }

    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Creating Account...';
    btn.disabled = true;

    try {
      const res = await API.post('/api/auth/register', payload);

      if (res.success) {
        showToast('Success', res.message || 'Account created successfully! Redirecting...', 'success');
        btn.innerHTML = '<i class="fa-solid fa-check"></i> Success! Entering Portal...';
        setTimeout(() => {
          window.location.href = res.redirect || '/';
        }, 800);
      } else {
        showToast('Registration Failed', res.message || 'Could not complete registration.', 'error');
        btn.innerHTML = originalText;
        btn.disabled = false;
      }
    } catch (err) {
      showToast('Error', 'An unexpected error occurred during signup.', 'error');
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  });
}
