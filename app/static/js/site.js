/******************************************************************
 static/js/site.js  –  Theme‑Toggle + Countdown (CSP‑konform)
******************************************************************/
(() => {
  /* -------- Light/Dark Toggle ------------------------------- */
  const root   = document.documentElement;
  const btn    = document.querySelector('#themeToggle');
  const icon   = btn?.firstElementChild;
  const key    = 'theme';
  const apply  = t => {
    root.dataset.theme = t;
    icon?.classList.toggle('fa-sun',  t === 'light');
    icon?.classList.toggle('fa-moon', t === 'dark');
    localStorage.setItem(key, t);
  };
  apply(localStorage.getItem(key) || 'light');
  btn?.addEventListener('click', () =>
    apply(root.dataset.theme === 'dark' ? 'light' : 'dark'));

  /* -------- Countdown‑Badge -------------------------------- */
  const badge   = document.querySelector('#countdownBadge');
  if (!badge || !window.NEXT_ARRIVAL) return;

  const target = new Date(window.NEXT_ARRIVAL);
  const tick   = () => {
    const now  = new Date();
    let diff   = (target - now) / 1e3;                 // Sekunden
    if (diff <= 0) { badge.textContent = 'Heute!'; return; }
    const d = Math.floor(diff / 86400); diff %= 86400;
    const h = Math.floor(diff / 3600);  diff %= 3600;
    const m = Math.floor(diff / 60);
    badge.textContent = `${d} Tg ${h} Std ${m} Min`;
  };
  tick(); setInterval(tick, 60_000);
})();
