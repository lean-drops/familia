"""
Booking-Blueprint  ·  Owner-Only CRUD  ·  FullCalendar-Feed
"""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from typing import Dict
from flask import (
    Blueprint, jsonify, redirect, render_template, url_for, flash,
    request, abort
)
from flask_login import login_required, current_user
from flask_wtf import csrf
from sqlalchemy import and_
from app.models import db, Booking
from .forms import BookingForm

booking_bp = Blueprint("booking", __name__, template_folder="../templates/booking")

# ───────── Hilfs-Funktionen ─────────
def _countdown(target: date) -> Dict[str, int]:
    now  = datetime.now(timezone.utc).astimezone()
    tgt  = datetime.combine(target, datetime.min.time()).astimezone()
    diff = tgt - now
    if diff.total_seconds() <= 0:
        return {"days":0,"hours":0,"minutes":0}
    d = diff.days
    h, s = divmod(diff.seconds, 3600)
    m     = s // 60
    return {"days":d,"hours":h,"minutes":m}

def _overlap(start: date, end: date, exclude: int|None=None) -> bool:
    q = Booking.query.filter(Booking.start_date<=end, Booking.end_date>=start)
    if exclude: q = q.filter(Booking.id!=exclude)
    return db.session.query(q.exists()).scalar()

# ───────── Routes ─────────
@booking_bp.route("/")
@login_required
def calendar():
    next_own = (
        Booking.query.filter(Booking.user_id==current_user.id,
                             Booking.start_date>=date.today())
        .order_by(Booking.start_date).first()
    )
    return render_template(
        "booking/calendar.html",
        form=BookingForm(),
        next_arrival=next_own.start_date if next_own else None,
    )

@booking_bp.get("/events")
@login_required
def events():
    data=[]
    for b in Booking.query.all():
        can_edit = b.user_id == current_user.id
        data.append({
            "id":      b.id,
            "title":   f"{b.user.name}{' – '+b.companions if b.companions else ''}",
            "start":   b.start_date.isoformat(),
            "end":    (b.end_date+timedelta(days=1)).isoformat(),
            "allDay":  True,
            "editable":can_edit,        # per-Event Drag/Resize-Lock  :contentReference[oaicite:2]{index=2}
            "extendedProps": {
                "canEdit":   can_edit,
                "companions":b.companions,
            },
            "color":   b.user.color,
        })
    return jsonify(data)

@booking_bp.get("/booking/check-overlap")
@login_required
def check_overlap():
    try:
        start=date.fromisoformat(request.args["start_date"])
        end  =date.fromisoformat(request.args["end_date"])
    except (KeyError,ValueError):
        return jsonify({"error":"bad date"}),400
    excl=request.args.get("exclude_id",type=int)
    return jsonify({"overlap":_overlap(start,end,excl)})

@booking_bp.post("/booking/new")
@login_required
def new_booking():
    form = BookingForm()
    force= request.form.get("force")=="1"
    if not form.validate_on_submit():
        flash("Form ungültig","danger"); return redirect(url_for(".calendar"))
    if not force and _overlap(form.start_date.data,form.end_date.data):
        flash("Überschneidung!","danger"); return redirect(url_for(".calendar"))
    b=Booking(user_id=current_user.id,
              start_date=form.start_date.data,
              end_date=form.end_date.data,
              companions=form.companions.data or None)
    db.session.add(b); db.session.commit()
    flash("Buchung gespeichert.","success")
    return redirect(url_for(".calendar"))

@booking_bp.patch("/booking/update/<int:bid>")
@login_required
def update(bid:int):
    csrf.validate_csrf(request.headers.get("X-CSRFToken",""))
    b=Booking.query.get_or_404(bid)
    if b.user_id!=current_user.id:
        abort(403)                            # Owner-Gate  :contentReference[oaicite:3]{index=3}
    data=request.get_json() or {}
    start=date.fromisoformat(data["start_date"])
    end  =date.fromisoformat(data["end_date"])
    if not data.get("force") and _overlap(start,end,bid):
        abort(409)
    b.start_date,b.end_date=start,end
    db.session.commit()
    return "",204

@booking_bp.delete("/booking/delete/<int:bid>")
@login_required
def delete(bid:int):
    csrf.validate_csrf(request.headers.get("X-CSRFToken",""))
    b=Booking.query.get_or_404(bid)
    if b.user_id!=current_user.id:
        abort(403)
    db.session.delete(b); db.session.commit()
    return "",204
