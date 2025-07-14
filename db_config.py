"""
db_config.py ─ Zentraler Helper für die Datenbank-URL der Beach-House-App
────────────────────────────────────────────────────────────────────────────

Unterstützt zwei Varianten:

1.  Vollständige Verbindungskette per ``$DATABASE_URL``
    » mysql+pymysql://user:pass@host/db?charset=utf8mb4

2.  Einzelne ENV-Variablen (wie in deiner .flaskenv)
    » DB_HOST, DB_USER, DB_PASSWORD, DB_NAME [, DB_PORT]

Fällt beides weg und *allow_sqlite_fallback* ist True, wird auf
SQLite ``dev.db`` zurückgegriffen – praktisch für Tests ohne MySQL.

Beispiel Verwendung (config.py):

    from db_config import get_database_uri
    SQLALCHEMY_DATABASE_URI = get_database_uri()

Optional – Pool-Größe:
SQLAlchemy-Pooling wird **nicht** über die URL, sondern über
``SQLALCHEMY_ENGINE_OPTIONS`` gesetzt.  Wenn du `DB_POOL_SIZE`
definieren willst, kannst du sie dort weiterreichen.
"""

from pathlib import Path
import os
from urllib.parse import quote_plus, urlparse, uses_netloc
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────
#  Dotenv laden (erst .flaskenv, dann .env → Overrides möglich)
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".flaskenv", override=False)
load_dotenv(BASE_DIR / ".env",       override=False)

#  urllib kennt unser mysql-Schema
uses_netloc.extend(["mysql", "mysql+pymysql"])


# ─────────────────────────────────────────────────────────────
def _normalise_mysql(url: str) -> str:
    """Ersetzt mysql://  durch  mysql+pymysql://  (Treiber explizit)."""
    if url.startswith("mysql://"):
        return url.replace("mysql://", "mysql+pymysql://", 1)
    return url


def _build_from_parts() -> str | None:
    """
    Baut eine mysql+pymysql-URL aus diskreten ENV-Variablen.
    Gibt None zurück, falls nicht alle Pflichtfelder belegt sind.
    """
    host = os.getenv("DB_HOST")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    name = os.getenv("DB_NAME")
    port = os.getenv("DB_PORT")  # optional

    if not all([host, user, password, name]):
        return None

    creds = f"{quote_plus(user)}:{quote_plus(password)}"
    location = f"{host}:{port}" if port else host
    return f"mysql+pymysql://{creds}@{location}/{name}?charset=utf8mb4"


def get_database_uri(*, allow_sqlite_fallback: bool = True) -> str:
    """
    Liefert eine SQLAlchemy-kompatible Verbindungs-URL.

    Reihenfolge:
      1.  $DATABASE_URL             (direkter Override)
      2.  Einzelne DB_* Variablen   (selbst zusammengesetzt)
      3.  sqlite:///dev.db          (nur wenn erlaubt)

    Raises
    ------
    RuntimeError
        Wenn keine der Quellen eine brauchbare URL ergibt.
    """
    # 1. Vollständige URL vorhanden?
    raw = os.getenv("DATABASE_URL")
    if raw:
        raw = _normalise_mysql(raw)
        parsed = urlparse(raw)
        if parsed.scheme and parsed.netloc:
            return raw

    # 2. Aus Einzelwerten bauen
    assembled = _build_from_parts()
    if assembled:
        return assembled

    # 3. Fallback auf SQLite
    if allow_sqlite_fallback:
        return f"sqlite:///{BASE_DIR / 'dev.db'}"

    raise RuntimeError("No database configuration found in environment.")
