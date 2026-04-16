from datetime import datetime
from flask import current_app

from .extensions import db
from .models import Booking


def release_expired_bookings():
    now = datetime.utcnow()
    expired = Booking.query.filter(Booking.status == "confirmed", Booking.end_time <= now).all()
    changed = 0
    for b in expired:
        b.status = "expired"
        changed += 1
    if changed:
        db.session.commit()
    current_app.logger.debug(f"Expired bookings released: {changed}")


