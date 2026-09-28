"""Factual counts for the dashboards. No ranking of a 'best' stall."""

from datetime import timedelta

from app.models import FoodItem, Order, OrderStatus, Payment, PaymentStatus, User
from app.models.user import Role, utcnow


def owner_summary(stall) -> dict:
    now = utcnow()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week = start - timedelta(days=start.weekday())
    orders = Order.query.filter_by(stall_id=stall.id)
    today = orders.filter(Order.created_at >= start)
    paid_today = [
        order.total
        for order in today
        if order.payment and order.payment.status in (PaymentStatus.SUCCESS, PaymentStatus.CASH_PAID)
    ]
    return {
        "orders_today": today.count(),
        "preparing": orders.filter_by(status=OrderStatus.PREPARING).count(),
        "ready": orders.filter_by(status=OrderStatus.READY).count(),
        "revenue_today": sum(paid_today, 0),
        "orders_week": orders.filter(Order.created_at >= week).count(),
        "cancelled": orders.filter_by(status=OrderStatus.CANCELLED).count(),
        "low_stock": FoodItem.query.filter(FoodItem.stall_id == stall.id, FoodItem.stock_quantity <= 5).all(),
        "active": orders.filter(Order.status.in_(OrderStatus.ACTIVE)).order_by(Order.created_at.asc()).all(),
    }


def admin_summary() -> dict:
    return {
        "students": User.query.filter_by(role=Role.STUDENT).count(),
        "owners": User.query.filter_by(role=Role.OWNER).count(),
        "orders": Order.query.count(),
        "revenue": _paid_total(),
    }


def _paid_total():
    rows = Payment.query.filter(Payment.status.in_((PaymentStatus.SUCCESS, PaymentStatus.CASH_PAID))).all()
    return sum((row.amount for row in rows), 0)


def orders_by_hour() -> list[int]:
    buckets = [0] * 24
    for order in Order.query.all():
        buckets[order.created_at.hour] += 1
    return buckets
