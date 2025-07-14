# app/api/routes.py  –  ersetzt die alte /events‑Funktion
# Blueprint‑Init bleibt unverändert (api_bp = Blueprint("api", …))

from __future__ import annotations

from datetime import date, datetime
from typing import List

from flask import request, jsonify, abort
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload
from sqlalchemy import and_

from . import api_bp
from app.models import db, Booking, User

# ─────────────────────────────────────────────────────────────
# /api/events  –  JSON‑Feed für FullCalendar
# ─────────────────────────────────────────────────────────────
@api_bp.route("/events")
@login_required
def events() -> "flask.wrappers.Response":
    """
    Liefert alle Buchungen als JSON‑Liste.

    Optionale Query‑Parameter:
        ?user=<int>             – nur Events dieses Users
        ?from=<YYYY‑MM‑DD>      – Start‑Datum Filter
        ?to=<YYYY‑MM‑DD>        – End‑Datum   Filter

    Response‑Schema pro Event:
        {
          "id": 17,
          "title": "Silvia Habegger – Max, Julia",
          "start": "2025-08-03",
          "end":   "2025-08-10",
          "color": "#5ea77a",
          "days_left": 42         # 0, wenn bereits gestartet
        }
    """
    # ── Query‑Parameter parsen ───────────────────────────────
    try:
        user_id: int | None = request.args.get("user", type=int)
        date_from: date | None = (
            datetime.strptime(request.args["from"], "%Y-%m-%d").date()
            if "from" in request.args
            else None
        )
        date_to: date | None = (
            datetime.strptime(request.args["to"], "%Y-%m-%d").date()
            if "to" in request.args
            else None
        )
    except ValueError:
        abort(400, "Ungültiges Datumsformat; erwartet YYYY‑MM‑DD")

    # ── Basiskriterium: sichtbare Buchungen ──────────────────
    filters: List = []
    if user_id:
        filters.append(Booking.user_id == user_id)
    if date_from:
        filters.append(Booking.end_date >= date_from)
    if date_to:
        filters.append(Booking.start_date <= date_to)

    # ── Performante Abfrage mit eager‑Loaded User ────────────
    bookings = (
        Booking.query.options(joinedload(Booking.user))
        .filter(*filters)
        .order_by(Booking.start_date)
        .all()
    )

    today = date.today()
    data = [
        {
            "id": b.id,
            "title": f"{b.user.name}"
                     f"{' – ' + b.companions if b.companions else ''}",
            "start": b.start_date.isoformat(),
            "end": b.end_date.isoformat(),
            "color": b.user.color,
            "days_left": max((b.start_date - today).days, 0),
        }
        for b in bookings
    ]
    return jsonify(data)
