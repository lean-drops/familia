"""
Kalender‑ und Buchungs‑Blueprint (Beach‑House‑App)
Ergänzt um:
    •  /booking/check‑overlap   →  AJAX‑Kollisionstest (GET, JSON)
    •  /booking/new             →  akzeptiert optionales force‑Flag
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Dict

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    url_for,
    flash,
    request,          # NEU
)
from flask_login import login_required, current_user
from .forms import BookingForm
from app.models import db, Booking

# ---------------------------------------------------------------------------#
# Blueprint‑Initialisierung
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
    delta: timedelta = tgt - now
    if delta.total_seconds() <= 0:
        return {"days": 0, "hours": 0, "minutes": 0}

    days = delta.days
    hours, rest = divmod(delta.seconds, 3600)
    minutes = rest // 60
    return {"days": days, "hours": hours, "minutes": minutes}


# ---------------------------------------------------------------------------#
# Routen
# ---------------------------------------------------------------------------#
@booking_bp.route("/")
def index() -> str:
    next_start = None
    days_to_arrival = None
    if current_user.is_authenticated:
        next_start = (
            Booking.query.filter(
                Booking.user_id == current_user.id,
                Booking.start_date >= date.today(),
            )
            .order_by(Booking.start_date)
            .first()
        )
        if next_start:
            days_to_arrival = (next_start.start_date - date.today()).days
    return render_template(
        "index.html",
        next_arrival=next_start.start_date if next_start else None,
        days_to_arrival=days_to_arrival,
    )


@booking_bp.route("/calendar")
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


@booking_bp.route("/booking/check-overlap")
@login_required
def check_overlap():
    """
    AJAX‑Prüfung, ob der angefragte Zeitraum mit einer
    bestehenden Buchung kollidiert. Liefert JSON:

        { "overlap": true | false }
    """
    try:
        start = date.fromisoformat(request.args["start_date"])
        end = date.fromisoformat(request.args["end_date"])
    except (KeyError, ValueError):
        return jsonify({"error": "invalid or missing date(s)"}), 400

    conflict = Booking.overlaps(start, end).first() is not None
    return jsonify({"overlap": conflict})


@booking_bp.route("/booking/new", methods=["POST"])
@login_required
def new_booking():
    """
    Schreibt eine neue Buchung in die DB.
    Akzeptiert zusätzlich das verborgene Feld *force* (‚1‘ = erzwingen).
    """
    form = BookingForm()
    force = request.form.get("force") == "1"

    if not form.validate_on_submit():
        return redirect(url_for("booking.calendar"))

    if not force and Booking.overlaps(form.start_date.data, form.end_date.data).first():
        # Nur noch ein „danger“‑Flash, denn die Bestätigung läuft im Front‑End
        flash("Überschneidung mit einem bestehenden Aufenthalt!", "danger")
        return redirect(url_for("booking.calendar"))

    booking = Booking(
        user_id=current_user.id,
        start_date=form.start_date.data,
        end_date=form.end_date.data,
        companions=form.companions.data or None,
    )
    db.session.add(booking)
    db.session.commit()
    flash("Buchung gespeichert.", "success")
    return redirect(url_for("booking.calendar"))


@booking_bp.route("/events")
@login_required
def events():
    return jsonify([
        {
            "id": b.id,
            "title": f"{b.user.name}"
                     f"{' – ' + b.companions if b.companions else ''}",
            "start": b.start_date.isoformat(),
            "end": b.end_date.isoformat(),
            "color": b.user.color,
        }
        for b in Booking.query.all()
    ])


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
        {
            "date": upcoming.start_date.isoformat(),
            "countdown": _countdown(upcoming.start_date),
        }
    )
