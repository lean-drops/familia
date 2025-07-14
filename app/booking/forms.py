"""
 Vollständiges WTForms‑Modul für Buchungen.
"""
from flask_wtf import FlaskForm
from wtforms import DateField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError


class BookingForm(FlaskForm):
    start_date  = DateField("Von", validators=[DataRequired()])
    end_date    = DateField("Bis",  validators=[DataRequired()])
    companions  = StringField("Begleitung (optional)", validators=[Length(max=255)])
    submit      = SubmitField("Speichern")

    def validate_end_date(self, field):
        if field.data < self.start_date.data:
            raise ValidationError("Enddatum liegt vor dem Startdatum.")
