#!/usr/bin/env python
"""
app/models.py  –  Zentrales Datenmodell der Beach-House-App
────────────────────────────────────────────────────────────────────────────
Enthält:
• SQLAlchemy-Basiskonfiguration (db, migrate, login_manager)
• Models: Family, User, Booking, Invitation
• Hilfs- und Validierungsmethoden (overlaps, set_password, check_password)
Nur behutsame Erweiterung: Booking.nights + Booking.duration
"""
from __future__ import annotations

from datetime import datetime, date
from typing import Dict

from flask_login import LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash

# ──────────────────────────────────────────────────────────────────────────
# Basis-Objekte für App-Factory
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"   # Endpunkt für @login_required-Redirect

# ──────────────────────────────────────────────────────────────────────────
# MODELS
# ──────────────────────────────────────────────────────────────────────────
class Family(db.Model):
    __tablename__ = "families"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(80), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    # Auth ---------------------------------------------------------------
    username      = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    # Profil -------------------------------------------------------------
    first_name  = db.Column(db.String(80),  nullable=False)
    last_name   = db.Column(db.String(120), nullable=False)
    phone       = db.Column(db.String(20))
    color       = db.Column(db.String(7),   nullable=False, default="#0d6efd")
    family_id   = db.Column(db.Integer, db.ForeignKey("families.id"))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    family      = db.relationship("Family", backref="members")

    __table_args__ = (
        UniqueConstraint("first_name", "last_name", name="uq_user_fullname"),
    )

    # Convenience-Properties --------------------------------------------
    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    # Password-Helpers ---------------------------------------------------
    def set_password(self, password: str) -> None:
        """Speichert einen sicheren Hash des Passworts."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Vergleicht Klartext-Passwort mit dem gespeicherten Hash."""
        return check_password_hash(self.password_hash, password)


class Booking(db.Model):
    __tablename__ = "bookings"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    start_date = db.Column(db.Date,    nullable=False)
    end_date   = db.Column(db.Date,    nullable=False)
    companions = db.Column(db.String(255))          # optionale Begleitpersonen
    nights     = db.Column(db.Integer, nullable=False, default=1, server_default="1")  # NEU
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="bookings")

    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_booking_date_order"),
        Index("ix_booking_timerange", "start_date", "end_date"),
    )

    # ---------------------------------------------------------------
    @staticmethod
    def overlaps(start: date, end: date):
        """
        Liefert einen Query-Filter, der Buchungen zurückgibt, die sich
        mit dem Intervall [start, end] überschneiden.
        """
        return Booking.query.filter(
            Booking.end_date >= start,
            Booking.start_date <= end,
        )

    # ---------------------------------------------------------------
    @property
    def duration(self) -> int:
        """Gibt die tatsächliche Aufenthalts-Dauer in Nächten zurück."""
        return (self.end_date - self.start_date).days + 1


class Invitation(db.Model):
    __tablename__ = "invitations"

    id          = db.Column(db.Integer, primary_key=True)
    inviter_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    guest_name  = db.Column(db.String(120), nullable=False)
    guest_email = db.Column(db.String(120))
    start_date  = db.Column(db.Date,    nullable=False)
    end_date    = db.Column(db.Date,    nullable=False)
    accepted    = db.Column(db.Boolean, default=False, nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    inviter = db.relationship("User", backref="invitations")

    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_invitation_date_order"),
        Index("ix_invitation_timerange", "start_date", "end_date"),
    )
