from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from ..extensions import db
from ..models import ParkingArea, ParkingSlot, Booking, User


bp = Blueprint("admin", __name__, template_folder="../templates/admin")


@bp.get("/")
@login_required
def dashboard():
    # Basic guards for admin role
    if getattr(current_user, "role", "user") != "admin":
        flash("Access denied. Admin access required.", "danger")
        return redirect(url_for("parking.index"))
    
    # Get stats for dashboard
    users = User.query.all()
    areas = ParkingArea.query.all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    return render_template("admin/dashboard.html", 
                         users=users, 
                         areas=areas, 
                         recent_users=recent_users)


@bp.route("/areas", methods=["GET", "POST"])
@login_required
def areas():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()
        lat = request.form.get("latitude")
        lon = request.form.get("longitude")
        area = ParkingArea(name=name, address=address, latitude=float(lat) if lat else None, longitude=float(lon) if lon else None)
        db.session.add(area)
        db.session.commit()
        flash("Area added", "success")
        return redirect(url_for("admin.areas"))
    areas = ParkingArea.query.all()
    return render_template("admin/areas.html", areas=areas)


@bp.route("/slots", methods=["GET", "POST"])
@login_required
def slots():
    if request.method == "POST":
        area_id = int(request.form.get("area_id"))
        code = request.form.get("code", "").strip()
        slot = ParkingSlot(area_id=area_id, code=code)
        db.session.add(slot)
        db.session.commit()
        flash("Slot added", "success")
        return redirect(url_for("admin.slots"))
    areas = ParkingArea.query.all()
    slots = ParkingSlot.query.all()
    return render_template("admin/slots.html", areas=areas, slots=slots)


@bp.get("/bookings")
@login_required
def bookings():
    items = Booking.query.order_by(Booking.created_at.desc()).limit(200).all()
    return render_template("admin/bookings.html", bookings=items)


@bp.get("/users")
@login_required
def users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)


@bp.post("/users/<int:user_id>/verify")
@login_required
def verify_user(user_id):
    from ..email_utils import send_email
    
    if getattr(current_user, "role", "user") != "admin":
        flash("Access denied. Admin access required.", "danger")
        return redirect(url_for("admin.dashboard"))
    
    user = User.query.get_or_404(user_id)
    user.is_verified = True
    db.session.commit()
    
    # Send verification email
    if user.role == "slot_owner":
        subject = "Slot Owner Account Verified - Smart Parking"
        body = f"""
        Congratulations {user.name}!
        
        Your slot owner account has been verified and approved.
        
        You can now:
        - Add parking areas
        - Manage slots
        - View booking analytics
        - Start earning money!
        
        Login to your account: {request.url_root}auth/login
        
        Best regards,
        Smart Parking Team
        """
        send_email(subject, [user.email], body)
        flash(f"User {user.name} verified successfully! Verification email sent.", "success")
    else:
        flash(f"User {user.name} verified successfully!", "success")
    
    return redirect(url_for("admin.users"))


@bp.post("/users/<int:user_id>/reject")
@login_required
def reject_user(user_id):
    from ..email_utils import send_email
    
    if getattr(current_user, "role", "user") != "admin":
        flash("Access denied. Admin access required.", "danger")
        return redirect(url_for("admin.dashboard"))
    
    user = User.query.get_or_404(user_id)
    
    # Send rejection email
    if user.role == "slot_owner":
        subject = "Slot Owner Account Application - Additional Information Required"
        body = f"""
        Hello {user.name},
        
        Thank you for your interest in becoming a slot owner with Smart Parking.
        
        We need additional information to verify your business credentials:
        - Valid business license
        - Proof of parking facility ownership/management rights
        - Insurance documentation
        
        Please contact us at admin@smartparking.local with the required documents.
        
        Best regards,
        Smart Parking Team
        """
        send_email(subject, [user.email], body)
        flash(f"Rejection email sent to {user.name}.", "info")
    
    return redirect(url_for("admin.users"))


