"""
Centralised Flask configuration for the Beach-House booking app.

• Imports `get_database_uri()` from db_config.py so Dev/Prod both
  resolve the correct SQLAlchemy URL.
• Loads `.env` before anything else, keeping Heroku and local identical.
• Offers a simple `config_map` so create_app() can pick the right config.
"""

from pathlib import Path
from dotenv import load_dotenv
import os
from db_config import get_database_uri

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)


class BaseConfig:
    """Shared defaults for all environments."""
    # ────────────────────────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    WTF_CSRF_ENABLED: bool = True

    # Logging (used by setup_logging.py)
    LOG_DIR: str = os.getenv("LOG_DIR", str(BASE_DIR / "logs"))

    # JSON responses stay in original order


    JSON_SORT_KEYS: bool = False


class DevConfig(BaseConfig):
    """Local development + tests."""
    ENV: str = "development"
    DEBUG: bool = True
    SQLALCHEMY_ECHO: bool = False
    SQLALCHEMY_DATABASE_URI: str = get_database_uri(allow_sqlite_fallback=True)


class ProdConfig(BaseConfig):
    """Heroku production dynos."""
    ENV: str = "production"
    DEBUG: bool = False
    TESTING: bool = False
    SQLALCHEMY_DATABASE_URI: str = get_database_uri(allow_sqlite_fallback=False)

    # Secure cookies over HTTPS on Heroku
    SESSION_COOKIE_SECURE: bool = True
    REMEMBER_COOKIE_SECURE: bool = True
    PREFERRED_URL_SCHEME: str = "https"


# Mapping used by create_app()
config_map = {
    "development": DevConfig,
    "production": ProdConfig,
}
