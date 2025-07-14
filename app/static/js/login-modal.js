/* ============================================================
   login-modal.js – Muestra el modal de login al cargar la página
   Cumple CSP: se carga desde 'self' y lleva nonce en la etiqueta
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  const modalEl = document.getElementById('loginModal');
  if (modalEl) {
    new bootstrap.Modal(modalEl, { backdrop: 'static', keyboard: false })
      .show();                                     // abre justo al cargar
  }
});
