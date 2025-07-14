#!/usr/bin/env python
"""
run.py  –  Einstiegspunkt für lokale Entwicklung UND Heroku-Dyno

✓ Lädt zuerst .flaskenv (CLI-Standard) und danach .env
  → so bleiben beide Dateien kompatibel, ohne sich gegenseitig zu überschreiben.
✓ Initialisiert das Logging (setup_logging.py), BEVOR weitere Imports passieren.
✓ Stellt die Flask-App global als `app` bereit, damit Gunicorn sie findet.
"""

from pathlib import Path
import os
from dotenv import load_dotenv
from setup_logging import configure_logging

# ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent

# 1️⃣  Environment-Variablen laden
load_dotenv(BASE_DIR / ".flaskenv", override=False)   # zuerst CLI-Defaults
load_dotenv(BASE_DIR / ".env", override=False)        # dann private Overrides

# 2️⃣  Logging sofort aktivieren
configure_logging()

# 3️⃣  App-Factory importieren (erst JETZT, damit Config + Logger bereit sind)
from app import create_app  # noqa: E402, pylint: disable=C0413

app = create_app()

# ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # PyCharm-Run-Konfiguration greift hier
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 7878)),
        debug=os.getenv("FLASK_ENV") == "development",
    )
