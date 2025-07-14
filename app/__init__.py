"""
app/__init__.py — Application‑Factory der “Familia”‑App
Vollständig, lauffähig, Juli 2025
────────────────────────────────────────────────────────────
• JSON‑Logging (structlog)                    • Sentry‑Tracing (optional)
• Babel 4 Locale‑Selector + Jinja‑Globale     • CSP via Flask‑Talisman
• Flask‑Limiter, Flask‑Caching                • Health‑Endpoint /ping
• Registriert alle Blueprints (auth, booking, api)
"""

from __future__ import annotations

import os
from datetime import datetime
from importlib import import_module

from flask import Flask, request, session
from flask_babel import Babel, get_locale
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
import sentry_sdk
import structlog

from .models import db, migrate, login_manager           # SQLAlchemy, Alembic, Login
from .auth.routes import auth_bp
from .booking.routes import booking_bp
from .api.routes import api_bp

# ─────────────────────────────────────────────────────────────
#  E X T E N S I O N S
# ─────────────────────────────────────────────────────────────
babel   = Babel()
cache   = Cache()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/day", "50/hour"],
    storage_uri=os.getenv("RATELIMIT_STORAGE_URL", "memory://"),   # In‑Memory für Dev
)
talisman = Talisman(
    content_security_policy_nonce_in=["script"],   # ▶ fügt Nonce in <script>
    force_https=True,
)

# ─────────────────────────────────────────────────────────────
#  F A C T O R Y
# ─────────────────────────────────────────────────────────────
def create_app() -> Flask:
    env        = os.getenv("FLASK_ENV", "production")
    config_map = import_module("config").config_map

    app = Flask(__name__)
    app.config.from_object(config_map[env])

    # ── Logging (Structlog → JSON) ───────────────────────────
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            app.config.get("LOG_LEVEL", "INFO")
        ),
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
    )

    # ── Sentry (optional) ────────────────────────────────────
    if (dsn := os.getenv("SENTRY_DSN")):
        sentry_sdk.init(dsn=dsn, traces_sample_rate=0.15)

    # ── Core‑Extensions ──────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # ── Babel 4 Locale‑Selector ──────────────────────────────
    babel.init_app(
        app,
        locale_selector=lambda: (
            session.get("lang")
            or request.accept_languages.best_match(["de", "es", "en"])
            or "de"
        ),
    )

    #  Globale Helfer für Templates
    app.jinja_env.globals.update(
        get_locale=get_locale,                   #  voller Babel‑Context
        active_lang=lambda: get_locale().upper(),        #  DE / ES / EN
        supported_languages=[
            ("de", "Deutsch"),
            ("es", "Español"),
            ("en", "English"),
        ],
    )

    # ── Caching (Single‑Node → Simple, Prod → Redis) ─────────
    cache.init_app(
        app,
        config={
            "CACHE_TYPE": "SimpleCache"
            if env == "development"
            else "RedisCache",
            "CACHE_REDIS_URL": os.getenv(
                "REDIS_URL", "redis://localhost:6379/0"
            ),
            "CACHE_DEFAULT_TIMEOUT": 300,
        },
    )

    # ── Rate‑Limiting ────────────────────────────────────────
    limiter.init_app(app)  # storage_uri schon oben gesetzt

    # ── Content‑Security‑Policy ──────────────────────────────
    CSP = {
        "default-src": ["'self'"],
        "img-src": ["'self'", "data:"],
        "script-src": [
            "'self'",
            "https://cdn.jsdelivr.net",
            "https://cdnjs.cloudflare.com",
        ],
        "style-src": [
            "'self'",
            "https://cdn.jsdelivr.net",
            "https://cdnjs.cloudflare.com",
            "https://fonts.googleapis.com",
            "'unsafe-inline'",
        ],
        "font-src": [
            "'self'",
            "https://fonts.gstatic.com",
            "https://cdnjs.cloudflare.com",
            "data:",
        ],
    }
    talisman.init_app(app, content_security_policy=CSP)

    # ── Blueprints ───────────────────────────────────────────
    for bp in (auth_bp, booking_bp, api_bp):
        app.register_blueprint(bp)

    # ── Health‑Endpoint ──────────────────────────────────────
    @app.get("/ping")
    def ping():
        """Kleiner Health‑Check für Load‑Balancers / Uptime‑Robots."""
        return {"status": "ok", "time": datetime.utcnow().isoformat()}

    return app
