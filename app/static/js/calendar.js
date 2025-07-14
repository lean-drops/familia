/* ───── static/js/calendar.js ──────────────────────────────────────────────
   Komplett‑Script für die Kalender‑Seite.

   ✓ Initialisiert FullCalendar (v6.x, global build) im Bootstrap‑Look
   ✓ Öffnet das WTForms‑Modal bei Date‑Range‑Auswahl
   ✓ Prüft Überschneidungen via AJAX (/booking/check‑overlap)
   ✓ Erlaubt „Trotzdem speichern“ per Fenster‑Bestätigung
   ✓ Sendet das Formular (inkl. CSRF‑Token) per fetch an /booking/new
   ✓ Lädt nach erfolgreicher Buchung den Kalender neu
   ✓ Zeigt optional einen Live‑Countdown in #nextArrivalCountdown
   ─────────────────────────────────────────────────────────────────────── */

(() => {
  'use strict';

  /* Utility: DOM ready ---------------------------------------------------- */
  const onReady = (cb) =>
    document.readyState === 'loading'
      ? document.addEventListener('DOMContentLoaded', cb, { once: true })
      : cb();

  /* Utility: ISO‑Date (YYYY‑MM‑DD) from Date‑Objekt ----------------------- */
  const toISODate = (d) => d.toISOString().slice(0, 10);

  /* Main — runs when DOM finished ---------------------------------------- */
  onReady(() => {
    /* ── FullCalendar Setup ─────────────────────────────────────────────── */
    const calEl = document.getElementById('calendar');
    if (!calEl) return;

    const calendar = new FullCalendar.Calendar(calEl, {
      locale: 'de-ch',
      timeZone: 'local',
      themeSystem: 'bootstrap5',
      firstDay: 1,
      height: 'auto',
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,timeGridDay',
      },
      selectable: true,
      selectMirror: true,
      eventTimeFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
      events: '/events',

      /* Date‑Range via Drag / Click → Modal füllen */
      select(selectionInfo) {
        // FullCalendar liefert end (exklusiv) → einen Tag zurück
        const endInclusive = new Date(selectionInfo.end);
        endInclusive.setDate(endInclusive.getDate() - 1);

        openBookingModal(toISODate(selectionInfo.start), toISODate(endInclusive));
        calendar.unselect();
      },
    });

    calendar.render();

    /* ── Booking‑Modal Logik ────────────────────────────────────────────── */
    const modalEl = document.getElementById('bookingModal');
    const bsModal = modalEl ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    const form    = modalEl ? modalEl.querySelector('form') : null;

    function openBookingModal(startISO, endISO) {
      if (!bsModal || !form) return;

      form.querySelector('input[name="start_date"]').value = startISO;
      form.querySelector('input[name="end_date"]').value   = endISO;
      form.querySelector('input[name="companions"]').value = '';
      form.querySelector('input[name="force"]')?.remove();          // altes Flag säubern

      bsModal.show();
    }

    /* Submit‑Handler mit Kollisions‑Check -------------------------------- */
    if (form) {
      form.addEventListener('submit', async (evt) => {
        evt.preventDefault();

        const fd = new FormData(form);
        const qs = new URLSearchParams({
          start_date: fd.get('start_date'),
          end_date:   fd.get('end_date'),
        });

        /* 1 — AJAX an /booking/check‑overlap */
        const res  = await fetch(`/booking/check-overlap?${qs}`, {
          headers: { Accept: 'application/json' },
        });
        const json = await res.json();

        if (json.error) {
          alert(`Fehler: ${json.error}`);
          return;
        }

        /* 2 — Bei Konflikt bestätigen lassen */
        if (json.overlap) {
          const keep = window.confirm(
            'Für den gewählten Zeitraum existiert bereits eine Buchung.\n' +
            'Trotzdem speichern?'
          );
          if (!keep) {
            bsModal.hide();
            return;
          }
          fd.append('force', '1');
        }

        /* 3 — Endgültiger POST (FormData enthält CSRF‑Token) */
        await fetch('/booking/new', { method: 'POST', body: fd });

        /* 4 — Neu laden, damit FullCalendar aktualisierte Daten holt */
        window.location.reload();
      });
    }

    /* ── Live‑Countdown (optional) ─────────────────────────────────────── */
    const badgeEl = document.getElementById('nextArrivalCountdown');
    const tgtISO  = window.NEXT_ARRIVAL;
    if (badgeEl && tgtISO) {
      const target = new Date(`${tgtISO}T00:00:00`);
      const update = () => {
        const now   = new Date();
        let diff    = target - now;
        if (diff < 0) diff = 0;

        const days    = Math.floor(diff / 86_400_000);
        const hours   = Math.floor((diff % 86_400_000) / 3_600_000);
        const minutes = Math.floor((diff % 3_600_000) / 60_000);

        badgeEl.textContent = `${days} Tage ${hours} h ${minutes} min`;
      };
      update();
      setInterval(update, 30_000);
    }
  });
})();
