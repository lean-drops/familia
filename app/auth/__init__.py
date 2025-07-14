"""
app/auth/__init__.py  –  Blueprint‑Factory für das Auth‑Modul
-------------------------------------------------------------
Wird in *app/__init__.py* mit  `app.register_blueprint(auth_bp)`  eingebunden.
"""

from flask import Blueprint

auth_bp = Blueprint(
    "auth",
    __name__,
    template_folder="../templates/auth",
    url_prefix="/auth",
)
