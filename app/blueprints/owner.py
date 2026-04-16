from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from ..extensions import db
from ..models import ParkingArea, ParkingSlot, Booking, User


bp = Blueprint("owner", __name__, url_prefix="/owner")


@bp.get("/")
@login_required
def dashboard():
    if current_user.role != "slot_owner":
        flash("Access denied. Slot owner access required.", "danger")
        return redirect(url_for("parking.index"))
    
    if not current_user.is_verified:
        flash("Your slot owner account is pending verification. Please wait for admin approval.", "warning")
        return redirect(url_for("auth.verification_status"))
    
    # Get owner's areas
    areas = ParkingArea.query.filter_by(owner_id=current_user.id).all()
    
    # Calculate stats
    total_slots = sum(len(area.slots) for area in areas)
    total_bookings = Booking.query.join(ParkingSlot).join(ParkingArea).filter(
        ParkingArea.owner_id == current_user.id
    ).count()
    
    # Recent bookings
    recent_bookings = Booking.query.join(ParkingSlot).join(ParkingArea).filter(
        ParkingArea.owner_id == current_user.id
    ).order_by(Booking.created_at.desc()).limit(10).all()
    
    return render_template("owner/dashboard.html", 
                         areas=areas, 
                         total_slots=total_slots,
                         total_bookings=total_bookings,
                         recent_bookings=recent_bookings)


@bp.route("/areas", methods=["GET", "POST"])
@login_required
def areas():
    if current_user.role != "slot_owner":
        flash("Access denied. Slot owner access required.", "danger")
        return redirect(url_for("parking.index"))
    
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        hourly_rate = float(request.form.get("hourly_rate", 2.50))
        description = request.form.get("description", "").strip()
        amenities = request.form.get("amenities", "").strip()
        operating_hours = request.form.get("operating_hours", "24/7").strip()
        
        area = ParkingArea(
            name=name,
            address=address,
            latitude=float(latitude) if latitude else None,
            longitude=float(longitude) if longitude else None,
            owner_id=current_user.id,
            hourly_rate=hourly_rate,
            description=description,
            amenities=amenities,
            operating_hours=operating_hours
        )
        db.session.add(area)
        db.session.commit()
        flash("Parking area added successfully!", "success")
        return redirect(url_for("owner.areas"))
    
    areas = ParkingArea.query.filter_by(owner_id=current_user.id).all()
    return render_template("owner/areas.html", areas=areas)


@bp.route("/areas/<int:area_id>/slots", methods=["GET", "POST"])
@login_required
def area_slots(area_id):
    if current_user.role != "slot_owner":
        flash("Access denied. Slot owner access required.", "danger")
        return redirect(url_for("parking.index"))
    
    area = ParkingArea.query.filter_by(id=area_id, owner_id=current_user.id).first_or_404()
    
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if code:
            slot = ParkingSlot(area_id=area.id, code=code)
            db.session.add(slot)
            db.session.commit()
            flash("Slot added successfully!", "success")
        return redirect(url_for("owner.area_slots", area_id=area_id))
    
    slots = ParkingSlot.query.filter_by(area_id=area.id).all()
    return render_template("owner/slots.html", area=area, slots=slots)


@bp.get("/areas/<int:area_id>/bookings")
@login_required
def area_bookings(area_id):
    if current_user.role != "slot_owner":
        flash("Access denied. Slot owner access required.", "danger")
        return redirect(url_for("parking.index"))
    
    area = ParkingArea.query.filter_by(id=area_id, owner_id=current_user.id).first_or_404()
    
    # Get bookings for this area
    bookings = Booking.query.join(ParkingSlot).filter(
        ParkingSlot.area_id == area.id
    ).order_by(Booking.created_at.desc()).all()
    
    return render_template("owner/bookings.html", area=area, bookings=bookings)


@bp.get("/analytics")
@login_required
def analytics():
    if current_user.role != "slot_owner":
        flash("Access denied. Slot owner access required.", "danger")
        return redirect(url_for("parking.index"))
    
    # Get owner's areas
    areas = ParkingArea.query.filter_by(owner_id=current_user.id).all()
    
    # Calculate analytics
    total_revenue = 0
    for area in areas:
        bookings = Booking.query.join(ParkingSlot).filter(
            ParkingSlot.area_id == area.id,
            Booking.status == "confirmed"
        ).all()
        for booking in bookings:
            hours = (booking.end_time - booking.start_time).total_seconds() / 3600
            total_revenue += hours * area.hourly_rate
    
    return render_template("owner/analytics.html", 
                         areas=areas, 
                         total_revenue=total_revenue)
