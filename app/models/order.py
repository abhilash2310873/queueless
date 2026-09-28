"""Cart, pickup slots, orders, reviews, and favorites."""

import uuid
from datetime import datetime

from app.extensions import db
from app.models.user import utcnow


class Cart(db.Model):
    __tablename__ = "carts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    stall_id = db.Column(db.Integer, db.ForeignKey("stalls.id"), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    user = db.relationship("User", backref=db.backref("cart", uselist=False))
    stall = db.relationship("Stall")
    items = db.relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("carts.id"), nullable=False, index=True)
    food_id = db.Column(db.Integer, db.ForeignKey("food_items.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    cart = db.relationship("Cart", back_populates="items")
    food = db.relationship("FoodItem")


class PickupSlot(db.Model):
    __tablename__ = "pickup_slots"

    id = db.Column(db.Integer, primary_key=True)
    stall_id = db.Column(db.Integer, db.ForeignKey("stalls.id"), nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    max_orders = db.Column(db.Integer, nullable=False)
    current_orders = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="OPEN")

    stall = db.relationship("Stall", backref="pickup_slots")

    @property
    def spaces_left(self) -> int:
        return max(self.max_orders - self.current_orders, 0)

    @property
    def label(self) -> str:
        return f"{self.start_time.strftime('%H:%M')}–{self.end_time.strftime('%H:%M')}"


class OrderStatus:
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    PREPARING = "PREPARING"
    READY = "READY"
    COLLECTED = "COLLECTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    ACTIVE = (PENDING, ACCEPTED, PREPARING, READY)
    # Allowed moves. Cancellation is only from PENDING.
    TRANSITIONS = {
        PENDING: {ACCEPTED, REJECTED, CANCELLED},
        ACCEPTED: {PREPARING},
        PREPARING: {READY},
        READY: {COLLECTED},
    }


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    queue_number = db.Column(db.String(20), unique=True, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    food_court_id = db.Column(db.Integer, db.ForeignKey("food_courts.id"), nullable=False)
    stall_id = db.Column(db.Integer, db.ForeignKey("stalls.id"), nullable=False, index=True)
    pickup_slot_id = db.Column(db.Integer, db.ForeignKey("pickup_slots.id"), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=OrderStatus.PENDING, index=True)
    # Random value signed into the QR. A forged token will not match this.
    qr_nonce = db.Column(db.String(64), nullable=True)
    preparing_started_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    user = db.relationship("User", backref="orders")
    food_court = db.relationship("FoodCourt")
    stall = db.relationship("Stall")
    pickup_slot = db.relationship("PickupSlot")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payment = db.relationship("Payment", back_populates="order", uselist=False)
    queue_record = db.relationship("QueueRecord", back_populates="order", uselist=False)
    review = db.relationship("Review", back_populates="order", uselist=False)


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(36), db.ForeignKey("orders.id"), nullable=False, index=True)
    food_id = db.Column(db.Integer, db.ForeignKey("food_items.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(8, 2), nullable=False)
    prep_time_minutes = db.Column(db.Integer, nullable=False)

    order = db.relationship("Order", back_populates="items")
    food = db.relationship("FoodItem")


class QueueRecord(db.Model):
    __tablename__ = "queue_records"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(36), db.ForeignKey("orders.id"), unique=True, nullable=False)
    position = db.Column(db.Integer, nullable=False)
    estimated_wait_minutes = db.Column(db.Integer, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    order = db.relationship("Order", back_populates="queue_record")


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(36), db.ForeignKey("orders.id"), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    stall_id = db.Column(db.Integer, db.ForeignKey("stalls.id"), nullable=False)
    food_id = db.Column(db.Integer, db.ForeignKey("food_items.id"), nullable=True)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    order = db.relationship("Order", back_populates="review")
    user = db.relationship("User")


class Favorite(db.Model):
    __tablename__ = "favorites"
    __table_args__ = (db.UniqueConstraint("user_id", "target_type", "target_id", name="uq_favorite"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    target_type = db.Column(db.String(20), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
