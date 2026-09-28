"""Payments store method, status, and a gateway reference. Never card data."""

from app.extensions import db
from app.models.user import utcnow


class PaymentStatus:
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    CASH_PENDING = "CASH_PENDING"
    CASH_PAID = "CASH_PAID"


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(36), db.ForeignKey("orders.id"), unique=True, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, index=True)
    gateway_reference = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    order = db.relationship("Order", back_populates="payment")
