from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, abort, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from ..extensions import db
from ..models import ParkingArea, ParkingSlot, Booking
from ..email_utils import send_email
import qrcode
import io
import base64


bp = Blueprint("parking", __name__)


@bp.get("/")
def index():
    areas = ParkingArea.query.all()
    return render_template("parking/index.html", areas=areas)


@bp.get("/area/<int:area_id>")
def area_detail(area_id: int):
    area = ParkingArea.query.get_or_404(area_id)
    return render_template("parking/area_detail.html", area=area, area_id=area.id)


@bp.get("/api/areas/<int:area_id>/availability")
def area_availability(area_id: int):
    try:
        area = ParkingArea.query.get_or_404(area_id)
        print(f"Loading availability for area {area_id}: {area.name}")
        print(f"Area has {len(area.slots)} slots")
        
        if not area.slots:
            return "<div class='alert alert-warning'>No slots available in this area.</div>"
        
        now = datetime.utcnow()
        active_bookings = (
            Booking.query.filter(
                Booking.slot_id.in_([s.id for s in area.slots]),
                Booking.status == "confirmed",
                Booking.start_time <= now,
                Booking.end_time > now,
            ).all()
        )
        busy_slot_ids = {b.slot_id for b in active_bookings}
        print(f"Found {len(active_bookings)} active bookings")
        
        # Render a simple grid fragment
        html = ["<div class='slot-grid'>"]
        for slot in area.slots:
            is_busy = slot.id in busy_slot_ids
            cls = "slot booked" if is_busy else "slot available"
            label = "🔴" if is_busy else "🟢"
            html.append(f"<div class='{cls}'>{label} {slot.code}</div>")
        html.append("</div>")
        
        result = "".join(html)
        print(f"Generated HTML: {result[:100]}...")
        return result
    except Exception as e:
        print(f"Error in area_availability: {e}")
        import traceback
        traceback.print_exc()
        return f"<div class='alert alert-danger'>Error loading availability: {str(e)}</div>"


@bp.post("/area/<int:area_id>/book")
@login_required
def create_booking(area_id: int):
    area = ParkingArea.query.get_or_404(area_id)
    slot_id = int(request.form.get("slot_id", 0))
    hours = int(request.form.get("hours", 1))
    if hours < 1:
        hours = 1
    slot = ParkingSlot.query.filter_by(id=slot_id, area_id=area.id).first()
    if not slot:
        abort(400)
    now = datetime.utcnow()
    end = now + timedelta(hours=hours)
    # Check conflicts
    conflict = (
        Booking.query.filter(
            Booking.slot_id == slot.id,
            Booking.status == "confirmed",
            Booking.end_time > now,
            Booking.start_time < end,
        ).first()
    )
    if conflict:
        flash("Slot already booked in selected time.", "warning")
        return redirect(url_for("parking.area_detail", area_id=area.id))
    # Dummy payment step: redirect to payment page
    return redirect(url_for("parking.payment", area_id=area.id, slot_id=slot.id, hours=hours))


@bp.get("/area/<int:area_id>/payment")
@login_required
def payment(area_id: int):
    slot_id = int(request.args.get("slot_id", 0))
    hours = int(request.args.get("hours", 1))
    area = ParkingArea.query.get_or_404(area_id)
    slot = ParkingSlot.query.filter_by(id=slot_id, area_id=area.id).first_or_404()
    price_per_hour = 2.50
    total = price_per_hour * max(1, hours)
    return render_template("parking/payment.html", area=area, slot=slot, hours=hours, total=total)


@bp.post("/area/<int:area_id>/confirm")
@login_required
def confirm_booking(area_id: int):
    slot_id = int(request.form.get("slot_id", 0))
    hours = int(request.form.get("hours", 1))
    area = ParkingArea.query.get_or_404(area_id)
    slot = ParkingSlot.query.filter_by(id=slot_id, area_id=area.id).first_or_404()
    now = datetime.utcnow()
    end = now + timedelta(hours=max(1, hours))
    # Final conflict check
    conflict = (
        Booking.query.filter(
            Booking.slot_id == slot.id,
            Booking.status == "confirmed",
            Booking.end_time > now,
            Booking.start_time < end,
        ).first()
    )
    if conflict:
        flash("Slot just got booked. Choose another.", "warning")
        return redirect(url_for("parking.area_detail", area_id=area.id))

    booking = Booking(
        user_id=current_user.id,
        slot_id=slot.id,
        start_time=now,
        end_time=end,
        status="confirmed",
        payment_ref=f"PMT-{int(now.timestamp())}-{current_user.id}",
    )
    db.session.add(booking)
    db.session.commit()

    # Generate QR code as PNG bytes
    qr_payload = {
        "booking_id": booking.id,
        "user": current_user.email,
        "slot": slot.code,
        "start": booking.start_time.isoformat(),
        "end": booking.end_time.isoformat(),
    }
    img = qrcode.make(str(qr_payload))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_bytes = buf.getvalue()

    # Save QR under static/img/bookings
    import os
    out_dir = os.path.join('app', 'static', 'img', 'bookings')
    os.makedirs(out_dir, exist_ok=True)
    qr_filename = f"booking_{booking.id}.png"
    qr_path = os.path.join(out_dir, qr_filename)
    with open(qr_path, 'wb') as f:
        f.write(qr_bytes)
    booking.qr_path = qr_path
    db.session.commit()

    # Email confirmation with QR attachment
    body = (
        f"Your booking is confirmed.\n"
        f"Booking ID: {booking.id}\n"
        f"Area: {slot.area.name}\n"
        f"Slot: {slot.code}\n"
        f"From: {booking.start_time}\n"
        f"To: {booking.end_time}\n"
    )
    send_email(
        subject="Smart Parking Booking Confirmation",
        recipients=[current_user.email],
        body=body,
        attachments=[(qr_filename, 'image/png', qr_bytes)],
    )
    return redirect(url_for("parking.booking_success", booking_id=booking.id))


@bp.get("/booking/<int:booking_id>/success")
@login_required
def booking_success(booking_id: int):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id and getattr(current_user, "role", "user") != "admin":
        abort(403)
    return render_template("parking/success.html", booking=booking)


@bp.get("/api/areas")
def api_areas():
    areas = ParkingArea.query.all()
    return jsonify([
        {
            "id": a.id,
            "name": a.name,
            "latitude": a.latitude,
            "longitude": a.longitude,
        } for a in areas
    ])


@bp.get("/api/test")
def api_test():
    areas = ParkingArea.query.all()
    area_data = []
    for area in areas:
        area_data.append({
            "id": area.id,
            "name": area.name,
            "slots_count": len(area.slots),
            "slots": [{"id": s.id, "code": s.code} for s in area.slots]
        })
    
    return jsonify({
        "status": "API is working", 
        "areas_count": len(areas),
        "areas": area_data
    })


