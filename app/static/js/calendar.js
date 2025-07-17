/* ───── static/js/calendar.js ───────────────────────────────────────────
   CRUD‑Frontend · Owner‑Only Editing · Info‑Modal · Touch & Haptics
   v2025‑07‑17 – responsive titles · 500 ms long‑press · clean structure
   ───────────────────────────────────────────────────────────────────── */
(() => {
  'use strict';

  /* ── Konfiguration & Konstanten ─────────────────────────────────── */
  const CONF = {
    LONG_PRESS: 500,               // 0,5 s für Drag/Select :contentReference[oaicite:0]{index=0}
    DRAG_MIN: 20,                  // Pixel bis Drag greift    :contentReference[oaicite:1]{index=1}
    HAPTIC: {
      TAP: 10,
      OPEN: [10, 30, 10],
      SUCCESS: [20, 40, 20],
      DELETE: [40, 60, 40],
    },
    TITLE_MIN_PX: 10,              // Schrumpf‑Untergrenze
  };

  /* ── Utility‑Funktionen ─────────────────────────────────────────── */
  const iso = (d) =>
    new Date(d.getTime() - d.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 10);

  const csrf = () =>
    document.querySelector('meta[name="csrf-token"]')?.content ?? '';

  const ready = (fn) =>
    document.readyState === 'loading'
      ? addEventListener('DOMContentLoaded', fn, { once: true })
      : fn();

  /* Vibrations‑Wrapper (graceful degradation) */
  const canVibrate =
    'vibrate' in navigator && typeof navigator.vibrate === 'function'; /* Feature‑Test :contentReference[oaicite:2]{index=2} */
  const vibe = (pattern) => canVibrate && navigator.vibrate(pattern);

  /* ── DOM ready ──────────────────────────────────────────────────── */
  ready(() => {
    const calEl = document.getElementById('calendar');
    if (!calEl) return;

    const isTouch = matchMedia('(pointer: coarse)').matches;

    /* FullCalendar‑Instanz ----------------------------------------- */
    const calendar = new FullCalendar.Calendar(calEl, {
      locale: 'de-ch',
      timeZone: 'local',
      themeSystem: 'bootstrap5',
      firstDay: 1,
      height: 'auto',
      selectable: true,
      editable: true,

      /* Mobile‑Tuning */
      longPressDelay: CONF.LONG_PRESS,        // Tap ≠ Drag   :contentReference[oaicite:3]{index=3}
      eventLongPressDelay: CONF.LONG_PRESS,
      selectLongPressDelay: CONF.LONG_PRESS,
      eventDragMinDistance: CONF.DRAG_MIN,    // Wackeln ignorieren :contentReference[oaicite:4]{index=4}

      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,timeGridDay',
      },
      eventTimeFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
      events: '/events',

      /* -------- Create / Quick‑Tap -------- */
      dateClick(info) {
        vibe(CONF.HAPTIC.TAP);
        openModal({
          id: null,
          canEdit: true,
          start: iso(info.date),
          end: iso(info.date),
          companions: '',
          title: '',
        });
      },

      select(sel) {
        const endInc = new Date(sel.end);
        endInc.setDate(endInc.getDate() - 1);
        vibe(CONF.HAPTIC.TAP);
        openModal({
          id: null,
          canEdit: true,
          start: iso(sel.start),
          end: iso(endInc),
          companions: '',
          title: '',
        });
        calendar.unselect();
      },

      /* -------- Read / Edit -------- */
      eventClick({ event: e }) {
        vibe(CONF.HAPTIC.OPEN);
        openEvent(e);
      },

      /* -------- Render‑Hook für smart Titles & Touch‑Fallback ----- */
      eventDidMount(info) {
        responsiveTitle(info.el);               // Schrift anpassen   :contentReference[oaicite:5]{index=5}
        if (!isTouch) return;
        info.el.addEventListener(
          'touchend',
          (ev) => {
            if (ev.changedTouches?.length === 1) {
              vibe(CONF.HAPTIC.OPEN);
              openEvent(info.event);
            }
          },
          { passive: true }
        );                                      // touch‑fallback :contentReference[oaicite:6]{index=6}
      },

      /* -------- Move / Resize -------- */
      eventDrop: handleMoveResize,
      eventResize: handleMoveResize,
    });

    calendar.render();

    /* ── Modal & Formular ────────────────────────────────────────── */
    const modalEl = document.getElementById('bookingModal');
    const bsModal = modalEl
      ? bootstrap.Modal.getOrCreateInstance(modalEl)
      : null;
    const form = modalEl?.querySelector('form');
    const delBtn = modalEl?.querySelector('#deleteBtn');

    function openEvent(e) {
      const endInc = e.end ? new Date(e.end) : new Date(e.start);
      if (e.end) endInc.setDate(endInc.getDate() - 1);
      openModal({
        id: e.id,
        canEdit: e.extendedProps.canEdit,
        start: iso(e.start),
        end: iso(endInc),
        companions: e.extendedProps.companions ?? '',
        title: e.title,
      });
    }

    function openModal(data) {
      if (!form || !bsModal) return;
      form.dataset.id = data.id ?? '';
      form.start_date.value = data.start;
      form.end_date.value = data.end;
      if (form.companions) form.companions.value = data.companions;
      if (form.title) form.title.value = data.title;
      const editable = !!data.canEdit;
      [...form.elements].forEach((el) => {
        if (el.name !== 'close') el.disabled = !editable;
      });
      delBtn?.classList.toggle('d-none', !editable || !data.id);
      bsModal.show();
    }

    /* -------- Submit ------------ */
    form?.addEventListener('submit', async (evt) => {
      evt.preventDefault();
      const fd = new FormData(form);
      const id = form.dataset.id;
      const chk = await fetchJSON(
        '/booking/check-overlap?' +
          new URLSearchParams({
            start_date: fd.get('start_date'),
            end_date: fd.get('end_date'),
            exclude_id: id || '',
          })
      );
      if (chk.overlap && !confirm('Überschneidung – trotzdem speichern?'))
        return;
      if (chk.overlap) fd.append('force', '1');

      if (id) {
        const res = await fetch(`/booking/update/${id}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf(),
          },
          body: JSON.stringify(Object.fromEntries(fd)),
        });
        if (!res.ok) return alert(`Fehler ${res.status}`);
      } else {
        await fetch('/booking/new', { method: 'POST', body: fd });
      }
      vibe(CONF.HAPTIC.SUCCESS);
      location.reload();
    });

    /* -------- Delete ------------ */
    delBtn?.addEventListener('click', async () => {
      const id = form?.dataset.id;
      if (!id || !confirm('Eintrag endgültig löschen?')) return;
      await fetch(`/booking/delete/${id}`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': csrf() },
      });
      vibe(CONF.HAPTIC.DELETE);
      location.reload();
    });

    /* -------- Move / Resize Handler ---- */
    async function handleMoveResize(info) {
      if (!info.event.extendedProps.canEdit) return info.revert();
      const endInc = info.event.end
        ? new Date(info.event.end)
        : new Date(info.event.start);
      if (info.event.end) endInc.setDate(endInc.getDate() - 1);
      const body = {
        start_date: iso(info.event.start),
        end_date: iso(endInc),
      };

      const chk = await fetchJSON(
        '/booking/check-overlap?' +
          new URLSearchParams({ ...body, exclude_id: info.event.id })
      );
      if (chk.overlap && !confirm('Kollision – trotzdem übernehmen?'))
        return info.revert();
      if (chk.overlap) body.force = 1;

      const res = await fetch(`/booking/update/${info.event.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrf(),
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) return info.revert();
      vibe(CONF.HAPTIC.TAP);
    }

    /* -------- Helper ------------ */
    async function fetchJSON(url, init = {}) {
      try {
        const r = await fetch(url, init);
        return await r.json();
      } catch {
        return {};
      }
    }

    /* Adaptive Font‑Sizing ---------------------------------------- */
    function responsiveTitle(eventEl) {
      const title = eventEl.querySelector('.fc-event-title');
      if (!title) return;

      const original = parseFloat(
        getComputedStyle(title).fontSize || '12'
      );
      let size = original;

      /* solange Inhalt überläuft und Schrift > min_px -> verkleinern */
      const fits = () =>
        title.scrollWidth <= eventEl.clientWidth &&
        title.scrollHeight <= eventEl.clientHeight;

      while (!fits() && size > CONF.TITLE_MIN_PX) {
        size -= 1;
        title.style.fontSize = size + 'px';
      }
    } /* inspiriert von community‑Lösung :contentReference[oaicite:7]{index=7} */
  });
})();
