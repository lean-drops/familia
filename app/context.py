# app/context.py
from datetime import date
from flask_login import current_user
from app.models import Booking

def register_context_processors(app):
    @app.context_processor
    def inject_next_arrivals():
        # globale Info – optional, hier nicht mehr benutzt
        overall = (Booking.query
                   .filter(Booking.start_date >= date.today())
                   .order_by(Booking.start_date)
                   .first())

        # persönliche nächste Anreise des eingeloggten Users
        own_next = None
        own_days_to_arrival = None
        if current_user.is_authenticated:
            own_next = (Booking.query
                        .filter(Booking.user_id == current_user.id,
                                Booking.start_date >= date.today())
                        .order_by(Booking.start_date)
                        .first())
            if own_next:
                own_days_to_arrival = (own_next.start_date - date.today()).days

        return dict(
            # falls du die globale Info noch irgendwo brauchst
            next_arrival_date = overall.start_date if overall else None,
            next_arrival_user = overall.user.name if overall else None,

            # *** exakt die Variablen, die base.html anspricht ***
            own_next_arrival_date = own_next.start_date if own_next else None,
            own_days_to_arrival   = own_days_to_arrival,
        )
