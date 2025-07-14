#!/usr/bin/env python
"""
utils/fill_colors.py  – Weist allen User‑Einträgen eine eindeutig
unterscheidbare #RRGGBB‑Farbe zu.

• Idempotent – aktualisiert nur Datensätze ohne gültigen Hex‑Wert
• Gleichmäßige Farbabstände via golden‑ratio Hue‑Verteilung
• Vollständiges Logging, optionaler --dry‑run
• Keine komplizierten SQL‑Funktionen → bulk_update_mappings()
"""

from __future__ import annotations

import logging
import math
import os
import re
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

# ─── Projekt‑Bootstrap ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".flaskenv", override=False)
load_dotenv(BASE_DIR / ".env",       override=False)

sys.path.append(str(BASE_DIR))
from app import create_app          # pylint: disable=wrong-import-position
from app.models import db, User     # pylint: disable=wrong-import-position

# ─── Logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("fill_colors")

HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


# ─── Hilfsfunktionen ───────────────────────────────────────────────
def _hls_to_hex(h: float, l: float = 0.5, s: float = 0.65) -> str:
    """HLS‑Float‑Tripel → #RRGGBB‑Hex."""
    import colorsys

    r, g, b = (int(v * 255) for v in colorsys.hls_to_rgb(h, l, s))
    return f"#{r:02X}{g:02X}{b:02X}"


def _golden_palette(n: int, offset: float = 0.17) -> List[str]:
    """Erzeugt *n* weit auseinanderliegende Farben (Hue‑Golden‑Ratio)."""
    phi = (math.sqrt(5) - 1) / 2  # 0.618…
    return [_hls_to_hex((offset + i * phi) % 1.0) for i in range(n)]


def _users_needing_color(session: Session) -> list[User]:
    """Liefert alle User ohne gültige Farbe."""
    stmt = select(User).order_by(User.id)
    return [
        u for u in session.scalars(stmt)
        if not u.color or not HEX_RE.match(u.color)
    ]


# ─── Main ──────────────────────────────────────────────────────────
def main(*, dry_run: bool = False) -> None:
    app = create_app()
    with app.app_context():
        session: Session = db.session

        needing = _users_needing_color(session)
        if not needing:
            log.info("✓ Alle User besitzen bereits gültige Farben – nichts zu tun.")
            return

        palette = _golden_palette(len(needing))
        updates = [
            {"id": user.id, "color": palette[idx]}
            for idx, user in enumerate(needing)
        ]

        if dry_run:
            for u in updates:
                log.info("~ DRY‑RUN: würde User #%d → %s setzen", u["id"], u["color"])
            log.info("✗ Dry‑Run beendet – keine Änderungen geschrieben.")
            return

        session.bulk_update_mappings(User, updates)
        session.commit()
        log.info("✓ %d Farben erfolgreich vergeben.", len(updates))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Vergibt Farben an User ohne gültigen Hex‑Wert.")
    parser.add_argument("--dry-run", action="store_true", help="Nur anzeigen, nicht speichern.")
    args = parser.parse_args()

    main(dry_run=args.dry_run)
