/* ───── static/js/calendar.js ──────────────────────────────────────────────
   Komplett-Script für die Kalender-Seite ― responsive auf Desktop & Mobile
   ✓ Initialisiert FullCalendar (v6.x, global build) im Bootstrap-Look
   ✓ Öffnet das WTForms-Modal bei Date-Range-Auswahl
   ✓ Erlaubt Drag-&-Drop-Verschiebung bestehender Buchungen
   ✓ Löscht Buchungen über eine dynamische Trash-Zone am unteren Rand
   ✓ Prüft Überschneidungen via AJAX (/booking/check-overlap)
   ✓ Erlaubt „Trotzdem speichern“ per Fenster-Bestätigung
   ✓ Persistiert Änderungen/Neuanlagen über /booking/new und /booking/update
   ✓ Löscht Buchungen über /booking/delete
   ✓ Lädt nach jeder Änderung den Kalender neu
   ✓ Zeigt optional einen Live-Countdown in #nextArrivalCountdown
   ─────────────────────────────────────────────────────────────────────── */

(() => {
  'use strict';

  /* Utility: DOM ready ---------------------------------------------------- */
  const onReady = (cb) =>
    document.readyState === 'loading'
      ? document.addEventListener('DOMContentLoaded', cb, { once: true })
      : cb();

  /* Utility: ISO-Date (YYYY-MM-DD) from Date-Objekt ----------------------- */
  const toISODate = (d) => d.toISOString().slice(0, 10);

  /* Utility: Inclusive ISO end date from FullCalendar event.end ---------- */
  const getInclusiveEnd = (end /* may be null */) => {
    if (!end) return null;
    const inc = new Date(end);
    inc.setDate(inc.getDate() - 1);
    return toISODate(inc);
  };

  /* Utility: fetch JSON helper ------------------------------------------- */
  const fetchJSON = async (url, opts = {}) => {
    const res = await fetch(url, { headers: { Accept: 'application/json' }, ...opts });
    return res.ok ? res.json() : { error: res.statusText || 'Server-Fehler' };
  };

  /* Main — runs when DOM finished ---------------------------------------- */
  onReady(() => {
    /* ── FullCalendar Setup ─────────────────────────────────────────────── */
    const calEl = document.getElementById('calendar');
    if (!calEl) return;

    const deleteBin   = document.getElementById('deleteBin');
    const detailsEl   = document.getElementById('detailsModal');
    const detailsBody = document.getElementById('detailsBody');
    const detailsModal = detailsEl ? bootstrap.Modal.getOrCreateInstance(detailsEl) : null;

    /* Dynamische Trash-Zone vorbereiten (Bootstrap-Klassen → kein Extra-CSS) */
    const trash = document.createElement('div');
    trash.id = 'calendarTrashZone';
    trash.className =
      'position-fixed bottom-0 start-50 translate-middle-x bg-danger text-white ' +
      'd-flex align-items-center justify-content-center rounded shadow px-4 py-2 fs-4';
    trash.style.zIndex = 9999;
    trash.style.display = 'none';
    trash.innerHTML = '<i class="bi bi-trash-fill me-2"></i>Buchung löschen';
    document.body.appendChild(trash);

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
      editable: true,           // Drag/Resize aktiv
      droppable: false,
      eventTimeFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
      events: '/events',
      editable: true,

      /* Date-Range via Drag / Click → Modal füllen ------------------------ */
      select(selectionInfo) {
        const endInclusive = new Date(selectionInfo.end);
        endInclusive.setDate(endInclusive.getDate() - 1);
        openBookingModal(toISODate(selectionInfo.start), toISODate(endInclusive));
        calendar.unselect();
      },

      eventDidMount(arg) {
        arg.el.addEventListener('click', (ev) => {
          if (ev.detail === 2) {
            showDetails(arg.event);
          }
        });
      },

      eventDrop(info) { updateBooking(info); },
      eventResize(info) { updateBooking(info); },
      eventDragStart() { deleteBin?.classList.add('show'); },
      eventDragStop(info) {
        if (!deleteBin) return;
        const rect = deleteBin.getBoundingClientRect();
        const x = info.jsEvent.clientX;
        const y = info.jsEvent.clientY;
        deleteBin.classList.remove('show');
        if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) {
          deleteBooking(info.event);
        }
      },

      /* ── Drag & Drop bestehender Events ───────────────────────────────── */
      eventDragStart() {
        trash.style.display = 'flex';
      },
      eventDragStop(info) {
        const { jsEvent, event } = info;
        const trashRect = trash.getBoundingClientRect();
        const x = jsEvent.clientX;
        const y = jsEvent.clientY;

        // Intersection prüfen
        const overTrash =
          x >= trashRect.left &&
          x <= trashRect.right &&
          y >= trashRect.top &&
          y <= trashRect.bottom;

        trash.style.display = 'none';

        if (overTrash) {
          deleteBooking(event);
        }
      },
      eventDrop(info) {
        updateBookingDates(info.event);
      },
      eventResize(info) {
        updateBookingDates(info.event);
      },
    });

    calendar.render();

    /* ── Booking-Modal Logik ───────────────────────────────────────────── */
    const modalEl = document.getElementById('bookingModal');
    const bsModal = modalEl ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    const form = modalEl ? modalEl.querySelector('form') : null;

    function openBookingModal(startISO, endISO) {
      if (!bsModal || !form) return;

      form.querySelector('input[name="start_date"]').value = startISO;
      form.querySelector('input[name="end_date"]').value = endISO;
      form.querySelector('input[name="companions"]').value = '';
      form.querySelector('input[name="force"]')?.remove(); // altes Flag säubern

      bsModal.show();
    }

    /* Submit-Handler mit Kollisions-Check -------------------------------- */
    if (form) {
      form.addEventListener('submit', async (evt) => {
        evt.preventDefault();

        const fd = new FormData(form);
        const qs = new URLSearchParams({
          start_date: fd.get('start_date'),
          end_date: fd.get('end_date'),
        });

        /* 1 — AJAX an /booking/check-overlap */
        const json = await fetchJSON(`/booking/check-overlap?${qs}`);
        if (json.error) {
          alert(`Fehler: ${json.error}`);
          return;
        }

        /* 2 — Bei Konflikt bestätigen lassen */
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

        /* 3 — Endgültiger POST (FormData enthält CSRF-Token) */
        await fetch('/booking/new', { method: 'POST', body: fd });

        /* 4 — Neu laden, damit FullCalendar aktualisierte Daten holt */
        window.location.reload();
      });
    }

    /* ── Funktionen für Drag-Änderungen & Löschen ──────────────────────── */
    async function updateBookingDates(event) {
      const startISO = toISODate(event.start);
      const endISO = getInclusiveEnd(event.end) || startISO; // falls end null

      // 1 — Overlap-Check
      const qs = new URLSearchParams({
        start_date: startISO,
        end_date: endISO,
        booking_id: event.id, // damit Backend eigene Buchung ignorieren kann
      });
      const ov = await fetchJSON(`/booking/check-overlap?${qs}`);
      if (ov.error) {
        alert(`Fehler: ${ov.error}`);
        event.revert();
        return;
      }

      if (ov.overlap) {
        const keep = window.confirm(
          'Für den neuen Zeitraum existiert bereits eine Buchung.\n' +
            'Trotzdem verschieben?'
        );
        if (!keep) {
          event.revert();
          return;
        }
      }

      // 2 — Update-Request
      const fd = new FormData();
      fd.append('booking_id', event.id);
      fd.append('start_date', startISO);
      fd.append('end_date', endISO);
      if (ov.overlap) fd.append('force', '1');

      await fetch('/booking/update', { method: 'POST', body: fd });

      // 3 — Neu laden (einfachste Lösung, statt Event-Objekt manuell updaten)
      window.location.reload();
    }

    async function deleteBooking(event) {
      if (
        !window.confirm(
          `Buchung vom ${toISODate(event.start)} wirklich endgültig löschen?`
        )
      )
        return;

      const fd = new FormData();
      fd.append('booking_id', event.id);

      await fetch('/booking/delete', { method: 'POST', body: fd });

      window.location.reload();
    }

    async function updateBooking(info) {
      const res = await fetch(`/booking/${info.event.id}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start: toISODate(info.event.start),
          end:   toISODate(info.event.end)
        })
      });
      if (!res.ok) info.revert();
    }

    async function deleteBooking(event) {
      await fetch(`/booking/${event.id}/delete`, { method: 'POST' });
      calendar.refetchEvents();
    }

    function showDetails(event) {
      if (!detailsModal || !detailsBody) return;
      detailsBody.innerHTML = `
        <p><strong>Gast:</strong> ${event.extendedProps.user}</p>
        <p><strong>Begleitung:</strong> ${event.extendedProps.companions || '-'}</p>
        <p><strong>Dauer:</strong> ${event.extendedProps.duration} Tage</p>
        <p><strong>Von:</strong> ${toISODate(event.start)}<br>
           <strong>Bis:</strong> ${toISODate(event.end)}</p>`;
      detailsModal.show();
    }

    /* ── Live-Countdown (optional) ─────────────────────────────────────── */
    const badgeEl = document.getElementById('nextArrivalCountdown');
    const tgtISO = window.NEXT_ARRIVAL;
    if (badgeEl && tgtISO) {
      const target = new Date(`${tgtISO}T00:00:00`);
      const update = () => {
        const now = new Date();
        let diff = target - now;
        if (diff < 0) diff = 0;

        const days = Math.floor(diff / 86_400_000);
        const hours = Math.floor((diff % 86_400_000) / 3_600_000);
        const minutes = Math.floor((diff % 3_600_000) / 60_000);

        badgeEl.textContent = `${days} Tage ${hours} h ${minutes} min`;
      };
      update();
      setInterval(update, 30_000);
    }
  });
})();
