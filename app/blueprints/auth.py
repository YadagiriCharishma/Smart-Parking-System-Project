from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from email_validator import validate_email, EmailNotValidError

from ..extensions import db, login_manager
from ..models import User


bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Welcome back!", "success")
            return redirect(url_for("parking.index"))
        flash("Invalid credentials", "danger")
    return render_template("auth/login.html")


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "user")
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        company_name = request.form.get("company_name", "").strip()
        license_number = request.form.get("license_number", "").strip()
        
        try:
            validate_email(email)
        except EmailNotValidError as e:
            flash(str(e), "danger")
            return render_template("auth/signup.html")
            
        if User.query.filter_by(email=email).first():
            flash("Email already registered", "warning")
            return render_template("auth/signup.html")
            
        # Create user based on role
        user = User(
            name=name, 
            email=email, 
            role=role,
            phone=phone,
            address=address
        )
        
        # Add role-specific fields
        if role == "slot_owner":
            user.company_name = company_name
            user.license_number = license_number
            user.is_verified = False  # Requires admin approval
            
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        if role == "slot_owner":
            flash("Account created! Your slot owner account is pending verification.", "success")
        else:
            flash("Account created. Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/signup.html")


@bp.get("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))


@bp.get("/verification-status")
@login_required
def verification_status():
    return render_template("auth/verification_status.html")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


