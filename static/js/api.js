/**
 * Blood Bank Management System - API & Helper Utility
 */

const API = {
  async get(url) {
    try {
      const response = await fetch(url);
      const data = await response.json();
      return data;
    } catch (error) {
      console.error(`GET ${url} failed:`, error);
      return { success: false, message: error.message || 'Network error' };
    }
  },

  async post(url, body = {}) {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await response.json();
      return data;
    } catch (error) {
      console.error(`POST ${url} failed:`, error);
      return { success: false, message: error.message || 'Network error' };
    }
  },

  async put(url, body = {}) {
    try {
      const response = await fetch(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await response.json();
      return data;
    } catch (error) {
      console.error(`PUT ${url} failed:`, error);
      return { success: false, message: error.message || 'Network error' };
    }
  },

  async getCurrentUser() {
    return await this.get('/api/auth/me');
  },

  async logout() {
    const res = await this.post('/api/auth/logout');
    window.location.href = res.redirect || '/';
  }
};

// Global HTML Escaping to prevent XSS
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Global Toast Notification Manager
function showToast(title, message, type = 'info', duration = 4000) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  const iconMap = {
    success: 'fa-solid fa-circle-check',
    error: 'fa-solid fa-circle-xmark',
    warning: 'fa-solid fa-triangle-exclamation',
    info: 'fa-solid fa-circle-info'
  };

  const iconClass = iconMap[type] || iconMap.info;

  toast.innerHTML = `
    <i class="${iconClass} toast-icon"></i>
    <div class="toast-content">
      <div class="toast-title">${escapeHtml(title)}</div>
      <div class="toast-message">${escapeHtml(message)}</div>
    </div>
    <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    <div class="toast-progress"></div>
  `;

  container.appendChild(toast);

  // Trigger animation
  setTimeout(() => toast.classList.add('show'), 10);

  // Auto remove
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// Formatting utilities
function formatCurrency(amount) {
  if (amount === undefined || amount === null) return '₹0.00';
  return '₹' + Number(amount).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

function formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return String(dateStr).substring(0, 10);
    return d.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  } catch {
    return dateStr;
  }
}

function formatDateTime(dateStr) {
  if (!dateStr) return 'N/A';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return String(dateStr).substring(0, 19);
    return d.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return dateStr;
  }
}

function getBadgeHTML(level) {
  switch (level) {
    case 'GOOD':
      return `<span class="badge badge-success"><span class="pulse-dot" style="background:#15803d;"></span> Good</span>`;
    case 'LOW':
      return `<span class="badge badge-alert"><span class="pulse-dot" style="background:#c2410c;"></span> Low Stock</span>`;
    case 'CRITICAL':
      return `<span class="badge badge-warning"><span class="pulse-dot" style="background:#b45309;"></span> Expiring Soon</span>`;
    case 'OUT OF STOCK':
      return `<span class="badge badge-danger"><span class="pulse-dot" style="background:#b91c1c;"></span> Out of Stock</span>`;
    case 'HIGH':
      return `<span class="badge badge-danger"><i class="fa-solid fa-fire"></i> Emergency (2h)</span>`;
    case 'MEDIUM':
      return `<span class="badge badge-warning"><i class="fa-solid fa-clock"></i> Urgent (4h)</span>`;
    case 'LOW_EMERGENCY':
    case 'LOW':
      return `<span class="badge badge-info"><i class="fa-solid fa-shield-halved"></i> Routine (8h)</span>`;
    case 'Pending':
      return `<span class="badge badge-alert"><i class="fa-solid fa-hourglass-half"></i> Pending</span>`;
    case 'Partially Approved':
      return `<span class="badge badge-warning"><i class="fa-solid fa-circle-half-stroke"></i> Partially Issued</span>`;
    case 'Approved':
      return `<span class="badge badge-success"><i class="fa-solid fa-check-double"></i> Approved / Fulfilled</span>`;
    case 'Rejected':
      return `<span class="badge badge-danger"><i class="fa-solid fa-xmark"></i> Rejected</span>`;
    case 'Cancelled':
      return `<span class="badge badge-secondary" style="background:#f1f5f9; color:#64748b; border:1px solid #e2e8f0;"><i class="fa-solid fa-ban"></i> Cancelled</span>`;
    case 'PAID':
      return `<span class="badge badge-success"><i class="fa-solid fa-receipt"></i> PAID</span>`;
    case 'PENDING':
      return `<span class="badge badge-danger"><i class="fa-solid fa-clock"></i> UNPAID</span>`;
    case 'Pending Screening':
      return `<span class="badge badge-warning"><i class="fa-solid fa-microscope"></i> Pending Screening</span>`;
    case 'Available':
      return `<span class="badge badge-success"><i class="fa-solid fa-check"></i> Available (FEFO)</span>`;
    case 'Issued':
      return `<span class="badge badge-info"><i class="fa-solid fa-truck-fast"></i> Dispatched</span>`;
    case 'Expired':
      return `<span class="badge badge-danger"><i class="fa-solid fa-skull-crossbones"></i> Expired</span>`;
    case 'Discarded':
      return `<span class="badge badge-danger"><i class="fa-solid fa-trash-can"></i> Discarded</span>`;
    default:
      return `<span class="badge badge-primary">${escapeHtml(level)}</span>`;
  }
}
