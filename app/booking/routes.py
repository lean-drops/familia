#!/usr/bin/env python
"""
routes.py  –  Kalender- und Buchungs-Blueprint (Beach-House-App)
────────────────────────────────────────────────────────────────────────────
Erweitert um ALLE Road-Map-Schritte 1 – 4:
    • /booking/<id>/update      – persistiert Drag/Resize-Änderungen
    • /booking/<id>/delete      – löscht Buchungen serverseitig
    • /booking/density          – Heat-Map-API (Tagesauslastung)
    • /booking/suggest          – liefert kollisionsfreie Alternativen
    • /events                   – liefert extendedProps (companions, user, nights)
    • /booking/check-overlap und /booking/new unverändert
Voraussetzung: Booking.nights-Spalte (siehe models.py) und Flask-Migrate-Upgrade.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Tuple

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    url_for,
    flash,
    request,
)
from flask_login import login_required, current_user
from sqlalchemy import func

from .forms import BookingForm
from app.models import db, Booking

# ---------------------------------------------------------------------------#
# Blueprint-Initialisierung
# ---------------------------------------------------------------------------#
booking_bp = Blueprint(
    "booking",
    __name__,
    template_folder="../templates/booking",
    url_prefix="/",
)

# ---------------------------------------------------------------------------#
# Hilfsfunktionen
# ---------------------------------------------------------------------------#
def _countdown(target: date) -> Dict[str, int]:
    now = datetime.now(timezone.utc).astimezone()
    tgt = datetime.combine(target, datetime.min.time()).astimezone()
    delta = tgt - now
    if delta.total_seconds() <= 0:
        return {"days": 0, "hours": 0, "minutes": 0}
    days = delta.days
    hours, rest = divmod(delta.seconds, 3600)
    minutes = rest // 60
    return {"days": days, "hours": hours, "minutes": minutes}


def _json_event(b: Booking) -> Dict:
    """Serialisiert ein Booking-Objekt inkl. extendedProps für FullCalendar."""
    return {
        "id": b.id,
        "title": b.user.name,
        "start": b.start_date.isoformat(),
        "end": b.end_date.isoformat(),
        "color": b.user.color,
        # ─ extendedProps ─
        "companions": b.companions,
        "user": b.user.name,
        "nights": b.nights,
    }

# ---------------------------------------------------------------------------#
# Seiten-Routen
# ---------------------------------------------------------------------------#
@booking_bp.route("/")
@login_required
def calendar() -> str:
    form = BookingForm()
    next_start = (
        Booking.query.filter(
            Booking.user_id == current_user.id,
            Booking.start_date >= date.today(),
        )
        .order_by(Booking.start_date)
        .first()
    )
    return render_template(
        "booking/calendar.html",
        form=form,
        next_arrival=next_start.start_date if next_start else None,
    )

# ---------------------------------------------------------------------------#
# Core-APIs  (unchanged + neue)
# ---------------------------------------------------------------------------#
@booking_bp.route("/booking/check-overlap")
@login_required
def check_overlap():
    try:
        start = date.fromisoformat(request.args["start_date"])
        end   = date.fromisoformat(request.args["end_date"])
    except (KeyError, ValueError):
        return jsonify({"error": "invalid or missing date(s)"}), 400
    conflict = Booking.overlaps(start, end).first() is not None
    return jsonify({"overlap": conflict})


@booking_bp.route("/booking/new", methods=["POST"])
@login_required
def new_booking():
    form  = BookingForm()
    force = request.form.get("force") == "1"

    if not form.validate_on_submit():
        return redirect(url_for("booking.calendar"))

    if not force and Booking.overlaps(form.start_date.data, form.end_date.data).first():
        flash("Überschneidung mit bestehender Buchung!", "danger")
        return redirect(url_for("booking.calendar"))

    booking = Booking(
        user_id=current_user.id,
        start_date=form.start_date.data,
        end_date=form.end_date.data,
        companions=form.companions.data or None,
        nights=(form.end_date.data - form.start_date.data).days + 1,
    )
    db.session.add(booking)
    db.session.commit()
    flash("Buchung gespeichert.", "success")
    return redirect(url_for("booking.calendar"))


@booking_bp.route("/booking/<int:booking_id>/update", methods=["POST"])
@login_required
def update_booking(booking_id: int):
    """Persistiert Drag- & Resize-Änderungen."""
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json(silent=True) or {}
    try:
        start = date.fromisoformat(data["start"])
        end   = date.fromisoformat(data["end"])
    except Exception:
        return jsonify({"error": "invalid data"}), 400

    force = data.get("force") == "1"
    if not force and Booking.overlaps(start, end).filter(Booking.id != booking_id).first():
        return jsonify({"overlap": True}), 409

    booking.start_date = start
    booking.end_date   = end
    booking.nights     = (end - start).days + 1
    db.session.commit()
    return jsonify({"status": "ok"})


@booking_bp.route("/booking/<int:booking_id>/delete", methods=["POST"])
@login_required
def delete_booking(booking_id: int):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        return jsonify({"error": "forbidden"}), 403
    db.session.delete(booking)
    db.session.commit()
    return jsonify({"status": "deleted"})


@booking_bp.route("/events")
@login_required
def events():
    """FullCalendar-Feed mit extendedProps."""
    return jsonify([_json_event(b) for b in Booking.query.all()])


# ---------------------------------------------------------------------------#
# Smart-Extras
# ---------------------------------------------------------------------------#
@booking_bp.route("/booking/density")
@login_required
def density():
    """
    Heat-Map-API: Tagesauslastung (0 – 1).
    Annahme: Haus = 1 Buchung gleichzeitig.
    """
    rows = (
        db.session.query(
            Booking.start_date.label("d"),
            func.count(Booking.id).label("cnt"),
        )
        .group_by(Booking.start_date)
        .all()
    )
    return jsonify([{"date": r.d.isoformat(), "density": r.cnt / 1.0} for r in rows])


@booking_bp.route("/booking/suggest")
@login_required
def suggest():
    """Schlägt bis zu 3 freie Blöcke gleicher Dauer innerhalb ±30 Tage vor."""
    try:
        want_start = date.fromisoformat(request.args["start"])
        want_end   = date.fromisoformat(request.args["end"])
    except (KeyError, ValueError):
        return jsonify({"error": "invalid date(s)"}), 400

    span = (want_end - want_start).days + 1
    window_start = want_start - timedelta(days=30)
    window_end   = want_end   + timedelta(days=30)

    suggestions: List[Tuple[date, date]] = []
    cursor = window_start
    while cursor <= window_end and len(suggestions) < 3:
        cand_end = cursor + timedelta(days=span - 1)
        if not Booking.overlaps(cursor, cand_end).first():
            suggestions.append((cursor, cand_end))
        cursor += timedelta(days=1)

    return jsonify(
        [
            {"start": s.isoformat(), "end": e.isoformat(), "nights": span}
            for s, e in suggestions
        ]
    )


@booking_bp.route("/api/next-arrival")
@login_required
def next_arrival():
    upcoming = (
        Booking.query.filter(
            Booking.user_id == current_user.id,
            Booking.start_date >= date.today(),
        )
        .order_by(Booking.start_date)
        .first()
    )
    if not upcoming:
        return jsonify({"countdown": None})
    return jsonify(
        {"date": upcoming.start_date.isoformat(),
         "countdown": _countdown(upcoming.start_date)}
    )
