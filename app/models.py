from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from .extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class User(UserMixin, db.Model, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)  # 'user', 'slot_owner', 'admin'
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    company_name = db.Column(db.String(200), nullable=True)  # For slot owners
    license_number = db.Column(db.String(100), nullable=True)  # For slot owners
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    profile_image = db.Column(db.String(300), nullable=True)

    bookings = db.relationship("Booking", back_populates="user", cascade="all,delete-orphan")
    owned_areas = db.relationship("ParkingArea", back_populates="owner", cascade="all,delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class ParkingArea(db.Model, TimestampMixin):
    __tablename__ = "parking_areas"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(300), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    hourly_rate = db.Column(db.Float, default=2.50, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    amenities = db.Column(db.Text, nullable=True)  # JSON string of amenities
    operating_hours = db.Column(db.String(100), nullable=True)  # e.g., "24/7" or "6AM-10PM"

    slots = db.relationship("ParkingSlot", back_populates="area", cascade="all,delete-orphan")
    owner = db.relationship("User", back_populates="owned_areas")


class ParkingSlot(db.Model, TimestampMixin):
    __tablename__ = "parking_slots"

    id = db.Column(db.Integer, primary_key=True)
    area_id = db.Column(db.Integer, db.ForeignKey("parking_areas.id", ondelete="CASCADE"), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False)

    area = db.relationship("ParkingArea", back_populates="slots")
    bookings = db.relationship("Booking", back_populates="slot", cascade="all,delete-orphan")


class Booking(db.Model, TimestampMixin):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    slot_id = db.Column(db.Integer, db.ForeignKey("parking_slots.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(db.String(20), default="confirmed", nullable=False)  # confirmed, cancelled, expired
    qr_path = db.Column(db.String(300), nullable=True)
    payment_ref = db.Column(db.String(100), nullable=True)

    user = db.relationship("User", back_populates="bookings")
    slot = db.relationship("ParkingSlot", back_populates="bookings")

    @property
    def is_active_now(self) -> bool:
        now = datetime.utcnow()
        return self.status == "confirmed" and self.start_time <= now < self.end_time

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.end_time


def create_default_data() -> None:
    if not ParkingArea.query.first():
        # Create default admin
        if not User.query.filter_by(email="admin@smartparking.local").first():
            admin = User(
                name="System Admin", 
                email="admin@smartparking.local", 
                role="admin",
                phone="+1-555-0001",
                is_verified=True
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.flush()
            
        # Create sample slot owner
        if not User.query.filter_by(email="owner@centralplaza.com").first():
            owner = User(
                name="John Smith",
                email="owner@centralplaza.com",
                role="slot_owner",
                phone="+1-555-0002",
                company_name="Central Plaza Parking LLC",
                license_number="CP-2024-001",
                address="123 Main St, Downtown",
                is_verified=True
            )
            owner.set_password("owner123")
            db.session.add(owner)
            db.session.flush()
            
            # Create area owned by slot owner
            area = ParkingArea(
                name="Central Plaza Parking",
                address="123 Main St, Downtown",
                latitude=37.7749,
                longitude=-122.4194,
                owner_id=owner.id,
                hourly_rate=3.00,
                description="Premium downtown parking with 24/7 security",
                amenities='["Security Cameras", "EV Charging", "Valet Service"]',
                operating_hours="24/7"
            )
            db.session.add(area)
            db.session.flush()
            
            # Create 20 slots
            for i in range(1, 21):
                db.session.add(ParkingSlot(area_id=area.id, code=f"CP-{i:02d}"))
                
        # Create another area for demo
        if not User.query.filter_by(email="owner@mallparking.com").first():
            mall_owner = User(
                name="Sarah Johnson",
                email="owner@mallparking.com",
                role="slot_owner",
                phone="+1-555-0003",
                company_name="Mall Parking Services",
                license_number="MPS-2024-002",
                address="456 Mall Ave, Shopping District",
                is_verified=True
            )
            mall_owner.set_password("owner123")
            db.session.add(mall_owner)
            db.session.flush()
            
            mall_area = ParkingArea(
                name="Shopping Mall Parking",
                address="456 Mall Ave, Shopping District",
                latitude=37.7849,
                longitude=-122.4094,
                owner_id=mall_owner.id,
                hourly_rate=2.00,
                description="Convenient mall parking with easy access to stores",
                amenities='["Covered Parking", "Shopping Cart Access", "Family Friendly"]',
                operating_hours="6AM-11PM"
            )
            db.session.add(mall_area)
            db.session.flush()
            
            # Create 15 slots for mall
            for i in range(1, 16):
                db.session.add(ParkingSlot(area_id=mall_area.id, code=f"MALL-{i:02d}"))
                
        db.session.commit()


