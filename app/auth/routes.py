"""
app/auth/routes.py  –  Login‑, Logout‑ und Benutzer‑Wechsel‑Routen
------------------------------------------------------------------
• Pass­wortloser Login via Dropdown/Modal
• Optionale Switch‑Route  /auth/switch/<id>  (bequem per Dropdown)
• Flash‑Feedback & CSRF‑geschützt
"""

from __future__ import annotations

from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    request,
    abort, session,
)
from flask_login import (
    login_user,
    logout_user,
    current_user,
    login_required,
)
from sqlalchemy import select
from app.models import db, User, login_manager
from . import auth_bp
from .forms import LoginForm


# ─────────────────────────────────────────────────────────────
# Login‑Manager Callback
# ─────────────────────────────────────────────────────────────
@login_manager.user_loader
def load_user(user_id: str) -> User | None:          # noqa: D401
    """Lädt User‑Objekt für Flask‑Login‑Session‑Cookie."""
    return db.session.get(User, int(user_id))


# ─────────────────────────────────────────────────────────────
# Routen
# ─────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():                                         # noqa: D401
    """
    Zeigt das Login‑Modal **oder** verarbeitet den Dropdown‑Submit.

    GET  /auth/login[?as=<id>]   →  Modal / User‑Switch
    POST /auth/login             →  Formular‑Submit
    """
    # 1️⃣  Benutzer bereits eingeloggt?
    if current_user.is_authenticated:
        return redirect(url_for("booking.calendar"))

    # 2️⃣  Query‑Parameter  ?as=<id>  →  Benutzer direkt wechseln
    user_id = request.args.get("as", type=int)
    if user_id:
        target = db.session.get(User, user_id)
        if not target:
            abort(404)
        login_user(target)
        flash(f"Eingeloggt als {target.name}", "success")
        return redirect(url_for("booking.calendar"))

    # 3️⃣  Klassischer Formular‑Login (Dropdown)
    form = LoginForm()
    form.user.choices = [
        (u.id, f"{u.first_name} {u.last_name}")
        for u in db.session.scalars(
            select(User).order_by(User.last_name, User.first_name)
        )
    ]

    if form.validate_on_submit():
        user = db.session.get(User, form.user.data)
        login_user(user)
        flash(f"Willkommen {user.first_name}!", "success")
        return redirect(url_for("booking.calendar"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():                                        # noqa: D401
    """Beendet die aktuelle Session und leitet zurück zur Login‑Seite."""
    logout_user()
    flash("Abgemeldet.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/switch/<int:user_id>")
@login_required
def switch_user(user_id: int):                       # noqa: D401
    """
    Bequeme Familien‑Funktion: Wechsel ohne Passwort oder Modals.
    Verwendet identische Checks wie der  ?as=<id>‑Parameter.
    """
    if current_user.id == user_id:
        return redirect(url_for("booking.calendar"))

    target = db.session.get(User, user_id)
    if not target:
        abort(404)

    logout_user()
    login_user(target)
    flash(f"Eingeloggt als {target.name}", "success")
    return redirect(url_for("booking.calendar"))

# app/auth/routes.py  – Auszug
@auth_bp.route("/set-language/<lang_code>")
def set_language(lang_code):
    if lang_code not in {"de", "es", "en"}:
        abort(404)

    session["lang"] = lang_code
    flash(f"Sprache gewechselt zu {lang_code.upper()}", "success")
    return redirect(request.args.get("next") or url_for("booking.calendar"))
