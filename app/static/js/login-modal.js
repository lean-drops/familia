/* ============================================================
   login-modal.js – Muestra el modal de login al cargar la página
   Cumple CSP: se carga desde 'self' y lleva nonce en la etiqueta
   ============================================================ */
(() => {
  const modalEl = document.getElementById('loginModal');
  if (modalEl) {
    bootstrap.Modal.getOrCreateInstance(modalEl, {
      backdrop: 'static',
      keyboard: false,
    }).show();                                    // abre justo al cargar
  }
})();
