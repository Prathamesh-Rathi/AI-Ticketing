// static/js/main.js

document.addEventListener('DOMContentLoaded', () => {

  document.querySelectorAll('.flash-bar').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.4s, transform 0.4s';
      el.style.opacity = '0';
      el.style.transform = 'translateY(-6px)';
      setTimeout(() => el.remove(), 400);
    }, 4000);
  });

  document.querySelectorAll('.chart-fill').forEach(el => {
    const target = el.style.width;
    el.style.width = '0';
    setTimeout(() => { el.style.width = target; }, 80);
  });

  document.querySelectorAll('.stat-number[data-count]').forEach(el => {
    const target = parseInt(el.dataset.count) || 0;
    if (isNaN(target) || target === 0) return;
    let current = 0;
    const step  = Math.ceil(target / 28);
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = current;
      if (current >= target) clearInterval(timer);
    }, 28);
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'n' && !isInputFocused()) {
      window.location.href = '/submit';
    }
    if (e.key === 't' && !isInputFocused()) {
      window.location.href = '/tickets';
    }
    if (e.key === 'd' && !isInputFocused()) {
      window.location.href = '/';
    }
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay.open').forEach(m => {
        m.classList.remove('open');
        document.body.style.overflow = '';
      });
    }
  });

});

function isInputFocused() {
  const el = document.activeElement;
  return el && (
    el.tagName === 'INPUT'    ||
    el.tagName === 'TEXTAREA' ||
    el.tagName === 'SELECT'   ||
    el.isContentEditable
  );
}

function openModal(id) {
  document.getElementById(id).classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal(id) {
  document.getElementById(id).classList.remove('open');
  document.body.style.overflow = '';
}

function confirmAction(msg) {
  return window.confirm(msg);
}

function copyText(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const original = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = original; }, 1500);
  });
}