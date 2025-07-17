# app/context.py
from datetime import date
from flask_login import current_user
from app.models import Booking

def register_context_processors(app):
    @app.context_processor
    def inject_next_arrivals():
        # ‑‑ Globale nächste Ankunft (irgendein Gast) ‑‑
        overall = (
            Booking.query.filter(Booking.start_date >= date.today())
            .order_by(Booking.start_date.asc()).first()
        )
        next_arrival_date = overall.start_date if overall else None

        # ‑‑ Nur für den eingelog gten Benutzer ‑‑
        own_next = None
        days_to_arrival = None
        if current_user.is_authenticated:
            own_next = (
                Booking.query.filter(
                    Booking.user_id == current_user.id,
                    Booking.start_date >= date.today(),
                )
                .order_by(Booking.start_date.asc()).first()
            )
            if own_next:
                days_to_arrival = (own_next.start_date - date.today()).days

        return dict(
            next_arrival_date=next_arrival_date,
            next_arrival_user=overall.user.name if overall else None,
            days_to_arrival=days_to_arrival,
        )
