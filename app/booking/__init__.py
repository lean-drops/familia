from flask import Blueprint
booking_bp = Blueprint(
    "booking", __name__, template_folder="../templates/booking", url_prefix="/"
)
