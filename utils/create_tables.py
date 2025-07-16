#!/usr/bin/env python
"""
utils/create_tables.py –  Datenbank-Bootstrap ohne Alembic
────────────────────────────────────────────────────────────────────────────
• Legt alle Tabellen an (db.create_all()).
• Rüstet fehlende Spalten in 'users' UND 'bookings' nach (username, password_hash,
  companions, nights, FK family_id …).
• Füllt nights rückwirkend für bestehende Buchungen (= end_date - start_date + 1).
• Seedet drei Families (Lahiguera, Tonev, Habegger).
Dieses Skript ist idempotent – erneutes Ausführen prüft zuerst,
ob Änderungen überhaupt noch nötig sind.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

# ─── ENV & Pfade ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".flaskenv", override=False)
load_dotenv(BASE_DIR / ".env",       override=False)

# ─── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
log = logging.getLogger("create_tables")

# ─── App-Import NACH ENV & Logger ─────────────────────────────────────────
sys.path.append(str(BASE_DIR))
from app import create_app               # noqa: E402
from app.models import db, Family        # noqa: E402

FAMILY_NAMES = ["Lahiguera", "Tonev", "Habegger"]
app = create_app()

# ──────────────────────────────────────────────────────────────────────────
# Hilfsfunktionen für Migrations-Snippets
# ──────────────────────────────────────────────────────────────────────────
def _ensure_username_column(inspector) -> None:
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "username" in cols:
        return

    # 1 – Spalte provisorisch anlegen (NULL erlaubt)
    db.session.execute(text(
        "ALTER TABLE users ADD COLUMN username VARCHAR(64) NULL AFTER id;"
    ))

    # 2 – Startwerte vergeben (+ Kollisionen auflösen)
    db.session.execute(text("""
        UPDATE users
        SET username = CASE
              WHEN first_name IS NOT NULL AND last_name IS NOT NULL
              THEN CONCAT(LOWER(first_name), '.', LOWER(last_name))
              ELSE CONCAT('user_', id)
            END
        WHERE username IS NULL OR username = '';
    """))
    db.session.execute(text("""
        UPDATE users u
        JOIN (
          SELECT username, COUNT(*) c FROM users
          GROUP BY username HAVING c > 1
        ) dup ON dup.username = u.username
        SET u.username = CONCAT(u.username, '_', u.id);
    """))

    # 3 – NOT NULL + UNIQUE aktivieren
    db.session.execute(text("""
        ALTER TABLE users
          MODIFY username VARCHAR(64) NOT NULL,
          ADD UNIQUE KEY uq_username (username);
    """))
    db.session.commit()
    log.info("✓ users.username erfolgreich migriert.")


def _ensure_password_hash_column(inspector) -> None:
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "password_hash" in cols:
        return
    db.session.execute(text(
        "ALTER TABLE users ADD COLUMN password_hash VARCHAR(256) NULL AFTER username;"
    ))
    db.session.commit()
    log.info("✓ users.password_hash angelegt (NULL erlaubt).")


def _ensure_nights_column(inspector) -> None:
    cols = {c["name"] for c in inspector.get_columns("bookings")}
    if "nights" in cols:
        return

    # 1 – Spalte mit Default 1 hinzufügen
    db.session.execute(text(
        "ALTER TABLE bookings "
        "ADD COLUMN nights INT NOT NULL DEFAULT 1 AFTER companions;"
    ))

    # 2 – Bestehende Datensätze korrekt berechnen
    db.session.execute(text("""
        UPDATE bookings
        SET nights = DATEDIFF(end_date, start_date) + 1;
    """))
    db.session.commit()
    log.info("✓ bookings.nights angelegt & rückwirkend befüllt.")


# ──────────────────────────────────────────────────────────────────────────
# Haupt-Bootstrap
# ──────────────────────────────────────────────────────────────────────────
with app.app_context():
    # Basis-Schema
    db.create_all()
    insp = inspect(db.engine)

    # users-Tabelle
    _ensure_username_column(insp)
    _ensure_password_hash_column(insp)

    user_cols = {c["name"] for c in insp.get_columns("users")}
    alters_u: list[str] = []
    if "family_id" not in user_cols:
        alters_u += [
            "ADD COLUMN family_id INT NULL",
            "ADD CONSTRAINT fk_users_family "
            "  FOREIGN KEY (family_id) REFERENCES families(id) "
            "  ON DELETE SET NULL",
            "ADD INDEX ix_users_family (family_id)",
        ]
    if "first_name" not in user_cols:
        alters_u.append("ADD COLUMN first_name VARCHAR(80) NOT NULL DEFAULT ''")
    if "last_name" not in user_cols:
        alters_u.append("ADD COLUMN last_name VARCHAR(120) NOT NULL DEFAULT ''")
    if "color" not in user_cols:
        alters_u.append("ADD COLUMN color CHAR(7) NULL COMMENT 'HTML-Hexfarbe'")

    if alters_u:
        db.session.execute(text("ALTER TABLE users " + ", ".join(alters_u) + ";"))
        db.session.commit()
        log.info("✓ users-Tabelle aktualisiert (%s).",
                 ", ".join(a.split()[2] for a in alters_u))
    else:
        log.info("✓ users-Tabelle bereits vollständig.")

    # bookings-Tabelle
    booking_cols = {c["name"] for c in insp.get_columns("bookings")}
    alters_b: list[str] = []
    if "companions" not in booking_cols:
        alters_b.append(
            "ADD COLUMN companions VARCHAR(255) NULL "
            "COMMENT 'Namen der Begleitpersonen'"
        )
    if alters_b:
        db.session.execute(text("ALTER TABLE bookings " + ", ".join(alters_b) + ";"))
        db.session.commit()
        log.info("✓ bookings-Tabelle aktualisiert (companions).")
    else:
        log.info("✓ bookings.companions bereits vorhanden.")

    # nights-Spalte sicherstellen
    _ensure_nights_column(insp)

    # Families seeden
    new_fams = [
        Family(name=n) for n in FAMILY_NAMES
        if not Family.query.filter_by(name=n).first()
    ]
    if new_fams:
        db.session.add_all(new_fams)
        db.session.commit()
        log.info("✓ %d Family-Einträge angelegt.", len(new_fams))
    else:
        log.info("✓ Families bereits vorhanden.")

log.info("Datenbank vollständig synchron – fertig.")
