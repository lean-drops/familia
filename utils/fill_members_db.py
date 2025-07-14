#!/usr/bin/env python
"""
utils/seed_users_from_vcf.py
────────────────────────────────────────────────────────────────────────────
• Liest .vcf/.vcard → extrahiert FN + erste TEL
• Splittet FN → first_name / last_name  (letztes Token = Nachname)
• Normalisiert via str.title()  (z. B. 'anna-maria' → 'Anna-Maria')
• Ermittelt family_id anhand des Nachnamens → Family.name  (case‑insensitive)
• Legt User an, falls Kombination (first_name, last_name) noch fehlt
Aufruf:
    python utils/seed_users_from_vcf.py  [/pfad/zur/datei.vcf]
    oder VCF_PATH Umgebungsvariable setzen
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

# ── 0. Dotenv ────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".flaskenv", override=False)
load_dotenv(BASE_DIR / ".env",       override=False)

# ── 1. VCARD‑Pfad ermitteln ─────────────────────────────────────
vcf_path: Optional[Path] = (
    Path(os.getenv("VCF_PATH"))
    if os.getenv("VCF_PATH")
    else Path(sys.argv[1]) if len(sys.argv) > 1 else None
)
if not vcf_path or not vcf_path.exists():
    # Optionaler GUI‑Dialog
    try:
        import tkinter as tk
        from tkinter import filedialog
        tk.Tk().withdraw()
        sel = filedialog.askopenfilename(
            title="VCARD auswählen",
            filetypes=[("vCard Dateien", "*.vcf *.vcard"), ("Alle Dateien", "*.*")],
        )
        vcf_path = Path(sel) if sel else None
    except ImportError:
        pass

if not vcf_path or not vcf_path.exists():
    raise FileNotFoundError("VCARD‑Datei nicht gefunden – VCF_PATH setzen oder als Arg übergeben.")

# ── 2. VCARD parsen ─────────────────────────────────────────────
VCARD_RE = re.compile(r"BEGIN:VCARD(.*?)END:VCARD", re.S | re.I)
FN_RE    = re.compile(r"\nFN[^:]*:(.+?)\r?\n", re.I)
TEL_RE   = re.compile(r"\nTEL[^:]*:(.+?)\r?\n", re.I)

def _qp(s: str) -> str:
    """Apple‑Contacts Quoted‑Printable → Klartext."""
    import quopri
    return quopri.decodestring(s).decode("utf‑8", errors="replace")

def _split(full: str) -> tuple[str, str]:
    """Heuristik: letztes Token = Nachname."""
    tokens = full.strip().split()
    if len(tokens) == 1:
        return tokens[0].title(), ""
    return " ".join(tokens[:-1]).title(), tokens[-1].title()

def parse_vcf(path: Path) -> List[Dict[str, str]]:
    contacts: list[dict[str, str]] = []
    raw = path.read_text(encoding="utf‑8", errors="ignore")
    for block in VCARD_RE.findall(raw):
        fn_m, tel_m = FN_RE.search(block), TEL_RE.search(block)
        if not fn_m:
            continue
        first, last = _split(_qp(fn_m.group(1)))
        phone = _qp(tel_m.group(1)).strip() if tel_m else None
        contacts.append({"first": first, "last": last, "phone": phone})
    return contacts

people = parse_vcf(vcf_path)
print(f"→ {len(people)} Kontakte gefunden in {vcf_path.name}")

# ── 3. DB‑Insert mit Family‑Lookup ──────────────────────────────
sys.path.append(str(BASE_DIR))
from app import create_app                      # noqa: E402
from app.models import db, User, Family         # noqa: E402

app = create_app()
new, skipped, no_family = 0, 0, 0

with app.app_context():
    # Cache Family‑Mapping (lower‑case)
    fam_map = {f.name.lower(): f.id for f in Family.query.all()}

    for p in people:
        if not p["first"]:
            continue

        # Existiert User schon?
        if User.query.filter_by(first_name=p["first"], last_name=p["last"]).first():
            skipped += 1
            continue

        fam_id = fam_map.get(p["last"].lower())
        if fam_id is None:
            no_family += 1  # Statistik, wird als NULL eingetragen

        db.session.add(
            User(
                first_name=p["first"],
                last_name=p["last"],
                phone=p["phone"],
                family_id=fam_id,
            )
        )
        new += 1

    db.session.commit()

print(
    f"✔︎ {new} neue User angelegt, "
    f"{skipped} übersprungen, "
    f"{no_family} ohne passende Family."
)
