/* ───── static/js/calendar.js ──────────────────────────────────────────────
   Vollständiges, aufgeräumtes Front-End für den Familien-Kalender
   ────────────────────────────────────────────────────────────────────────
   ✓ Initialisiert FullCalendar v6 im Bootstrap-Look (de-CH, local TZ)
   ✓ Drag & Drop + Resize mit Touch-Optimierung (eventDragMinDistance 3 px,
     longPressDelay 500 ms, dragScroll true) :contentReference[oaicite:0]{index=0}
   ✓ Doppelklick / Doppeltipp öffnet Detail-Modal (click-timer-Debounce) :contentReference[oaicite:1]{index=1}
   ✓ Einheitliche Trash-Zone #trashBin (erscheint nur während Drag)
   ✓ Live-Update / Delete via /booking/<id>/update | /delete
     → `calendar.refetchEvents()` statt Full-Reload :contentReference[oaicite:2]{index=2}
   ✓ Heat-Map-Layer: /booking/density liefert Background-Events nach
     Farblegende (0 frei → 1 belegt) :contentReference[oaicite:3]{index=3}
   ✓ Smart Suggest: bei Überschneidung holt /booking/suggest Alternativen
   ✓ Umfangreiche Debug-Logs für Dev-Console
   ─────────────────────────────────────────────────────────────────────── */

(() => {
  'use strict';

  // ───────────────────────────────────────────────────
  // Kleine Log-Helfer
  const log     = (...msg) => console.debug('[calendar]', ...msg);
  const warn    = (...msg) => console.warn ('[calendar]', ...msg);
  const error   = (...msg) => console.error('[calendar]', ...msg);

  // ───────────────────────────────────────────────────
  // Konstante API-Endpunkte an einer Stelle
  const API = {
    events   : '/events',
    overlap  : '/booking/check-overlap',
    new      : '/booking/new',
    update   : (id) => `/booking/${id}/update`,
    del      : (id) => `/booking/${id}/delete`,
    density  : '/booking/density',
    suggest  : '/booking/suggest',
  };

  // ───────────────────────────────────────────────────
  // DOM-Ready Wrapper
  const onReady = (cb) =>
    document.readyState === 'loading'
      ? document.addEventListener('DOMContentLoaded', cb, { once: true })
      : cb();

  // ───────────────────────────────────────────────────
  // Utility-Funktionen
  const toISODate  = (d) => d.toISOString().slice(0, 10);
  const fetchJSON  = (url, opts={}) =>
    fetch(url, { headers: { Accept: 'application/json' }, ...opts })
      .then((r) => (r.ok ? r.json() : Promise.reject(r)));

  // ───────────────────────────────────────────────────
  // Initialisierung
  onReady(async () => {
    log('DOM ready – Initialisiere Kalender');

    // ─── DOM-Elemente
    const calEl         = document.getElementById('calendar');
    const bookingModal  = bootstrap.Modal.getOrCreateInstance('#bookingModal');
    const detailModal   = bootstrap.Modal.getOrCreateInstance('#eventDetailModal');
    const detailBody    = document.querySelector('#eventDetailModal .modal-body');

    // Trash-Zone (falls nicht im HTML, on-the-fly erstellen)
    let trash = document.getElementById('trashBin');
    if (!trash) {
      trash = document.createElement('div');
      trash.id = 'trashBin';
      trash.className =
        'position-fixed bottom-0 start-50 translate-middle-x bg-danger text-white ' +
        'd-flex align-items-center justify-content-center rounded shadow px-4 py-2 fs-4';
      trash.innerHTML = '<i class="bi bi-trash-fill me-2"></i>Buchung löschen';
      document.body.appendChild(trash);
    }

    // ─── Heat-Map-Events vorab laden
    let heatmapEvents = [];
    try {
      const density = await fetchJSON(API.density);
      heatmapEvents = density.map((d) => ({
        start: d.date,
        end  : d.date,
        display: 'background',
        color  : `rgba(255,0,0,${d.density})`, // einfaches Rot-Alpha-Mapping
      }));
      log('Heatmap-Events geladen', heatmapEvents.length);
    } catch (e) {
      warn('Heatmap konnte nicht geladen werden', e);
    }

    if (!calEl) return error('#calendar nicht gefunden – Abbruch');

    // ─── Kalender-Instanz
    const calendar = new FullCalendar.Calendar(calEl, {
      locale               : 'de-ch',
      timeZone             : 'local',
      themeSystem          : 'bootstrap5',
      firstDay             : 1,
      height               : 'auto',
      selectable           : true,
      selectMirror         : true,
      editable             : true,
      eventDragMinDistance : 3,        // :contentReference[oaicite:4]{index=4}
      longPressDelay       : 500,      // :contentReference[oaicite:5]{index=5}
      dragScroll           : true,     // :contentReference[oaicite:6]{index=6}
      eventTimeFormat      : { hour:'2-digit', minute:'2-digit', hour12:false },
      headerToolbar: {
        left   : 'prev,next today',
        center : 'title',
        right  : 'dayGridMonth,timeGridWeek,timeGridDay',
      },
      events: (...args) => {
        // Kombiniert Buchungen + Heat-Map
        return fetchJSON(API.events)
          .then((evs) => [...evs, ...heatmapEvents])
          .then((all) => args[0](all))
          .catch((e) => { error('Events-Load-Error', e); args[1](e); });
      },

      // ─── Auswahl eines neuen Zeitraums → Buchungs-Modal
      select(info) {
        const endInc = new Date(info.end);
        endInc.setDate(endInc.getDate()-1);
        openBookingModal(toISODate(info.start), toISODate(endInc));
        calendar.unselect();
      },

      // ─── Klick vs. Doppelklick
      eventClick: (() => {
        let clickTimer = null;
        return async (info) => {
          if (clickTimer) {     // double tap / click
            clearTimeout(clickTimer);
            clickTimer = null;
            showDetails(info.event);
          } else {
            clickTimer = setTimeout(() => (clickTimer=null), 250);
          }
        };
      })(),

      // ─── Drag & Resize
      eventDragStart() { trash.classList.add('show'); },
      eventDragStop(info) {
        trash.classList.remove('show');
        const { clientX:x, clientY:y } = info.jsEvent;
        const r = trash.getBoundingClientRect();
        const over = x>=r.left && x<=r.right && y>=r.top && y<=r.bottom;
        if (over) return deleteBooking(info.event);
      },
      eventDrop  : (info) => updateBooking(info),
      eventResize: (info) => updateBooking(info),
    });

    calendar.render();
    log('FullCalendar gerendert');

    // ───────────────────────────────────────────────────
    // Booking-Modal-Logik  (Neuanlage)
    const form = document.querySelector('#bookingForm');
    function openBookingModal(startISO, endISO) {
      if (!form) return;
      form.start_date.value = startISO;
      form.end_date.value   = endISO;
      form.companions.value = '';
      form.querySelector('input[name="force"]')?.remove();
      bookingModal.show();
    }

    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      const qs = new URLSearchParams({
        start_date: fd.get('start_date'),
        end_date  : fd.get('end_date'),
      });
      try {
        const ov = await fetchJSON(`${API.overlap}?${qs}`);
        if (ov.overlap) {
          const keep = confirm('Es existiert bereits eine Buchung.\nTrotzdem speichern?');
          if (!keep) return bookingModal.hide();
          fd.append('force','1');
        }
        await fetch(API.new, { method:'POST', body: fd });
        calendar.refetchEvents();  // keine harte Seite-Refresh
        bookingModal.hide();
      } catch (err) { error('Save-Error', err); }
    });

    // ───────────────────────────────────────────────────
    // Drag-/Resize-Persistenz
    async function updateBooking(info) {
      const body = {
        start: toISODate(info.event.start),
        end  : toISODate(info.event.end),
      };
      try {
        await fetchJSON(API.update(info.event.id), {
          method : 'POST',
          headers: { 'Content-Type':'application/json' },
          body   : JSON.stringify(body),
        });
        calendar.refetchEvents();
        log('Update OK', body);
      } catch (e) {
        info.revert();
        if (e.status === 409) {
          warn('Konflikt – hole Vorschläge...');
          showSuggestions(body);
        } else error('Update-Error', e);
      }
    }

    // ───────────────────────────────────────────────────
    // Delete
    async function deleteBooking(event) {
      if (!confirm('Buchung wirklich endgültig löschen?')) return;
      try {
        await fetch(API.del(event.id), { method:'POST' });
        calendar.refetchEvents();
        log('Delete OK', event.id);
      } catch (e) { error('Delete-Error', e); }
    }

    // ───────────────────────────────────────────────────
    // Detail-Modal
    function showDetails(ev) {
      if (!detailModal) return;
      detailBody.innerHTML = `
        <p><strong>Gast:</strong> ${ev.extendedProps.user}</p>
        <p><strong>Begleitung:</strong> ${ev.extendedProps.companions || '—'}</p>
        <p><strong>Dauer:</strong> ${ev.extendedProps.nights} Nächte</p>
        <p>
          <strong>Von:</strong> ${toISODate(ev.start)}<br>
          <strong>Bis:</strong> ${toISODate(ev.end)}
        </p>`;
      detailModal.show();
    }

    // ───────────────────────────────────────────────────
    // Smart-Suggestions bei Kollision
    async function showSuggestions(body) {
      try {
        const qs = new URLSearchParams(body).toString();
        const alt = await fetchJSON(`${API.suggest}?${qs}`);
        if (!alt.length) return alert('Kein freier Zeitraum gefunden.');
        const msg = alt.map((a,i)=>
          `${i+1}. ${a.start} bis ${a.end} (${a.nights} Nä.)`).join('\n');
        if (confirm(`Konflikt.\nAlternative wählen?\n${msg}`)) {
          const best = alt[0];
          const evObj = calendar.getEventById(parseInt(body.booking_id||0));
          if (evObj) {
            evObj.setStart(best.start);
            evObj.setEnd(best.end);
            updateBooking({ event: evObj }); // rekursiv speichern
          }
        }
      } catch(e){ error('Suggest-Error', e); }
    }

    // ───────────────────────────────────────────────────
    // Countdown-Badge (unverändert)
    const badge = document.getElementById('nextArrivalCountdown');
    const tgtISO = window.NEXT_ARRIVAL;
    if (badge && tgtISO) {
      const target = new Date(`${tgtISO}T00:00:00`);
      const tick   = () => {
        const diff = Math.max(0, target - new Date());
        const days = Math.floor(diff / 86_400_000);
        const hrs  = Math.floor((diff % 86_400_000) / 3_600_000);
        const min  = Math.floor((diff % 3_600_000) / 60_000);
        badge.textContent = `${days} Tage ${hrs} h ${min} min`;
      };
      tick(); setInterval(tick, 30_000);
    }
  });
})();
