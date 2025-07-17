/******************************************************************
 static/js/site.js  –  Theme‑Toggle + Countdown (Bootstrap 5.3)
******************************************************************/
(() => {
  /* ---------- Light/Dark Toggle -------------------------------- */
  const root  = document.documentElement;
  const btn   = document.querySelector('#themeToggle');
  const icon  = btn?.firstElementChild;
  const key   = 'theme';

  const apply = mode => {
    root.setAttribute('data-bs-theme', mode);          // zentrales Attribut
    icon?.classList.toggle('fa-sun',  mode === 'light');
    icon?.classList.toggle('fa-moon', mode === 'dark');
    localStorage.setItem(key, mode);                   // Persistenz
  };

  apply(localStorage.getItem(key) ||
        root.getAttribute('data-bs-theme') || 'light');

  btn?.addEventListener('click', () =>
    apply(root.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark'));

  /* ---------- Countdown‑Badge ---------------------------------- */
  const badge = document.querySelector('#countdownBadge');
  if (!badge || !window.NEXT_ARRIVAL) return;

  const target = new Date(window.NEXT_ARRIVAL);
  const tick   = () => {
    const diff = (target - new Date()) / 1e3;
    if (diff <= 0) { badge.textContent = '¡Hoy!'; return; }

    let r = diff;
    const d = Math.floor(r / 86400); r %= 86400;
    const h = Math.floor(r /  3600); r %=  3600;
    const m = Math.floor(r /    60);

    badge.textContent = `${d}\u202FTg ${h}\u202FStd ${m}\u202FMin`;
  };
  tick(); setInterval(tick, 60_000);
})();
