"""
app/auth/forms.py  –  WTForms für den passwort­losen Familien‑Login
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    """Bietet ein Dropdown aller registrierten Nutzer."""
    user   = SelectField("Ich bin", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Einloggen")
