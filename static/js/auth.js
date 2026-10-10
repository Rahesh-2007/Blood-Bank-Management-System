/**
 * Blood Bank Management System - Authentication Controller
 * Handles role selection, password toggling, demo autofill, and login submissions.
 */

let currentRole = 'ADMIN'; // Default to Super Admin

document.addEventListener('DOMContentLoaded', () => {
  setupRoleCards();
  setupPasswordToggle();
  setupRememberMe();
  setupForgotPassword();
  setupLoginForm();
  updateRoleState(currentRole);
});

/**
 * Configure Role Selection Cards
 */
function setupRoleCards() {
  const roleCards = document.querySelectorAll('.role-select-card');
  roleCards.forEach(card => {
    card.addEventListener('click', () => {
      const selectedRole = card.dataset.role;
      if (selectedRole) {
        currentRole = selectedRole;
        updateRoleState(currentRole);
      }
    });
  });
}

/**
 * Update UI according to the selected role
 */
function updateRoleState(role) {
  // Update card active classes
  document.querySelectorAll('.role-select-card').forEach(card => {
    if (card.dataset.role === role) {
      card.classList.add('active');
    } else {
      card.classList.remove('active');
    }
  });

  const hospIdWrapper = document.getElementById('hosp-id-wrapper');
  const emailInput = document.getElementById('login-email');
  const demoHint = document.getElementById('demo-role-hint');

  if (role === 'HOSPITAL') {
    if (hospIdWrapper) hospIdWrapper.style.display = 'block';
    if (emailInput) emailInput.placeholder = 'metro@hospital.org';
    if (demoHint) demoHint.textContent = 'metro@hospital.org / metro123';
  } else if (role === 'ADMIN') {
    if (hospIdWrapper) hospIdWrapper.style.display = 'none';
    if (emailInput) emailInput.placeholder = 'admin@bloodbank.org';
    if (demoHint) demoHint.textContent = 'admin@bloodbank.org / admin123';
  } else {
    // COORDINATOR / Blood Bank Staff
    if (hospIdWrapper) hospIdWrapper.style.display = 'none';
    if (emailInput) emailInput.placeholder = 'coord@bloodbank.org';
    if (demoHint) demoHint.textContent = 'coord@bloodbank.org / coord123';
  }
}

/**
 * Password Visibility Toggle
 */
function setupPasswordToggle() {
  const toggleBtn = document.getElementById('password-toggle');
  const pwdInput = document.getElementById('login-password');
  const eyeIcon = document.getElementById('toggle-eye-icon');

  if (!toggleBtn || !pwdInput || !eyeIcon) return;

  toggleBtn.addEventListener('click', () => {
    if (pwdInput.type === 'password') {
      pwdInput.type = 'text';
      eyeIcon.classList.remove('fa-eye');
      eyeIcon.classList.add('fa-eye-slash');
    } else {
      pwdInput.type = 'password';
      eyeIcon.classList.remove('fa-eye-slash');
      eyeIcon.classList.add('fa-eye');
    }
  });
}

/**
 * Auto-fill demo credentials
 */
const quickFillBtn = document.getElementById('quick-fill-btn');
if (quickFillBtn) {
  quickFillBtn.addEventListener('click', () => {
    const emailInput = document.getElementById('login-email');
    const pwdInput = document.getElementById('login-password');
    const hospIdInput = document.getElementById('login-hosp-id');

    if (currentRole === 'COORDINATOR') {
      if (emailInput) emailInput.value = 'coord@bloodbank.org';
      if (pwdInput) pwdInput.value = 'coord123';
      if (hospIdInput) hospIdInput.value = '';
    } else if (currentRole === 'HOSPITAL') {
      if (hospIdInput) hospIdInput.value = 'HOSP101';
      if (emailInput) emailInput.value = 'metro@hospital.org';
      if (pwdInput) pwdInput.value = 'metro123';
    } else if (currentRole === 'ADMIN') {
      if (emailInput) emailInput.value = 'admin@bloodbank.org';
      if (pwdInput) pwdInput.value = 'admin123';
      if (hospIdInput) hospIdInput.value = '';
    }

    if (typeof showToast === 'function') {
      showToast('Autofilled', `Credentials filled for ${currentRole.toLowerCase()} role`, 'info');
    }
  });
}

/**
 * Remember Me Feature with localStorage
 */
function setupRememberMe() {
  const rememberCheck = document.getElementById('remember-me-check');
  const emailInput = document.getElementById('login-email');

  const savedEmail = localStorage.getItem('bb_remembered_email');
  const savedRole = localStorage.getItem('bb_remembered_role');

  if (savedEmail && emailInput) {
    emailInput.value = savedEmail;
    if (rememberCheck) rememberCheck.checked = true;
  }
  if (savedRole) {
    currentRole = savedRole;
  }
}

/**
 * Forgot Password Notice
 */
function setupForgotPassword() {
  const forgotLink = document.getElementById('forgot-password-link');
  if (!forgotLink) return;

  forgotLink.addEventListener('click', (e) => {
    e.preventDefault();
    if (typeof showToast === 'function') {
      showToast(
        'Password Assistance',
        'Please contact your network administrator at admin@bloodbank.org or your facility coordinator to reset your security credentials.',
        'info'
      );
    } else {
      alert('To reset your password, please contact the central administrator at admin@bloodbank.org.');
    }
  });
}

/**
 * Handle Login Form Submission
 */
function setupLoginForm() {
  const form = document.getElementById('login-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitBtn = document.getElementById('login-submit-btn');
    const btnText = document.getElementById('btn-text');
    const rememberCheck = document.getElementById('remember-me-check');

    const email = document.getElementById('login-email')?.value.trim();
    const password = document.getElementById('login-password')?.value.trim();
    const hospId = document.getElementById('login-hosp-id')?.value.trim();

    if (!email || !password) {
      if (typeof showToast === 'function') {
        showToast('Required Fields', 'Please provide both email address and password', 'warning');
      }
      return;
    }

    // Save or clear remember me email
    if (rememberCheck && rememberCheck.checked) {
      localStorage.setItem('bb_remembered_email', email);
      localStorage.setItem('bb_remembered_role', currentRole);
    } else {
      localStorage.removeItem('bb_remembered_email');
      localStorage.removeItem('bb_remembered_role');
    }

    const originalHtml = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Signing in...</span>';
    submitBtn.disabled = true;

    try {
      let endpoint = '';
      let payload = { email, password };

      if (currentRole === 'ADMIN') {
        endpoint = '/api/auth/admin/login';
      } else if (currentRole === 'COORDINATOR') {
        endpoint = '/api/auth/coordinator/login';
      } else if (currentRole === 'HOSPITAL') {
        endpoint = '/api/auth/hospital/login';
        if (hospId) payload.hospital_id = hospId;
      }

      const res = await API.post(endpoint, payload);

      if (res && res.success) {
        if (typeof showToast === 'function') {
          showToast('Success', res.message || 'Login successful! Redirecting...', 'success');
        }
        setTimeout(() => {
          window.location.href = res.redirect || '/';
        }, 500);
      } else {
        const errorMsg = res && res.message ? res.message : 'Invalid credentials provided';
        if (typeof showToast === 'function') {
          showToast('Login Failed', errorMsg, 'error');
        } else {
          alert(errorMsg);
        }
        submitBtn.innerHTML = originalHtml;
        submitBtn.disabled = false;
      }
    } catch (err) {
      console.error('Login error:', err);
      if (typeof showToast === 'function') {
        showToast('Error', 'Unable to reach the server. Please check your connection.', 'error');
      } else {
        alert('An error occurred during sign in.');
      }
      submitBtn.innerHTML = originalHtml;
      submitBtn.disabled = false;
    }
  });
}
