"""Place an order, move it through the allowed statuses, and keep the queue in step."""

import math
from decimal import Decimal

from flask import current_app
from sqlalchemy import update

from app.extensions import db
from app.models import (
    ActivityLog,
    Cart,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentStatus,
    PickupSlot,
    QueueRecord,
)
from app.notifications.services import notify
from app.orders.qr import QRError, assert_collectable, read_token, sign_order
from app.queue.services import queue_snapshot
from app.utils.stock import StockError, deduct_stock, restore_stock


class OrderError(Exception):
    pass


def place_order(user, slot_id: int, method: str) -> Order:
    cart = user.cart
    if cart is None or not cart.items or cart.stall_id is None:
        raise OrderError("Your cart is empty.")
    slot = db.session.get(PickupSlot, slot_id)
    if slot is None or slot.stall_id != cart.stall_id:
        raise OrderError("Choose a pickup slot for this stall.")
    lines = [
        {
            "food": line.food,
            "food_id": line.food_id,
            "name": line.food.name,
            "quantity": line.quantity,
            "price": line.food.price,
            "prep": line.food.prep_time_minutes,
            "stock": line.food.stock_quantity,
            "available": line.food.is_available,
        }
        for line in cart.items
    ]
    reserved = _reserve_slot(slot.id)
    if not reserved:
        raise OrderError("That pickup slot is full.")
    deducted = []
    try:
        for line in lines:
            if not line["available"] or line["stock"] < line["quantity"]:
                raise StockError(_remaining_message(line["food"]))
            deduct_stock(line["food_id"], line["quantity"])
            deducted.append((line["food_id"], line["quantity"]))
        total = sum((line["price"] * line["quantity"] for line in lines), Decimal("0.00"))
        tax = Decimal(str(current_app.config.get("TAX_RATE", 0)))
        total = (total * (Decimal("1") + tax)).quantize(Decimal("0.01"))
        order = Order(
            user_id=user.id,
            food_court_id=cart.stall.food_court_id,
            stall_id=cart.stall_id,
            pickup_slot_id=slot.id,
            total=total,
            payment_method=method,
            status=OrderStatus.PENDING,
        )
        db.session.add(order)
        db.session.flush()
        for line in lines:
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    food_id=line["food_id"],
                    name=line["name"],
                    quantity=line["quantity"],
                    unit_price=line["price"],
                    prep_time_minutes=line["prep"],
                )
            )
        status = PaymentStatus.CASH_PENDING if method == "CASH" else PaymentStatus.PENDING
        db.session.add(Payment(order_id=order.id, amount=total, method=method, status=status))
        if method == "CASH":
            _assign_queue(order)
            sign_order(order)
        db.session.add(ActivityLog(actor_id=user.id, action="order_created", detail=order.id))
        cart.items.clear()
        cart.stall_id = None
        db.session.commit()
    except (StockError, OrderError) as exc:
        for food_id, quantity in deducted:
            restore_stock(food_id, quantity)
        _release_slot(slot.id)
        raise OrderError(str(exc)) from exc
    notify(user.id, f"Order {order.queue_number or order.id[:8]} placed.")
    return order


def confirm_online_payment(order: Order, success: bool) -> None:
    if order.payment_method != "ONLINE" or order.payment.status != PaymentStatus.PENDING:
        raise OrderError("This order is not waiting for online payment.")
    if not success:
        order.payment.status = PaymentStatus.FAILED
        order.status = OrderStatus.CANCELLED
        for item in order.items:
            restore_stock(item.food_id, item.quantity)
        _release_slot(order.pickup_slot_id)
        db.session.commit()
        notify(order.user_id, "Payment failed. The order was cancelled and stock was returned.")
        return
    order.payment.status = PaymentStatus.SUCCESS
    order.payment.gateway_reference = "mock-" + order.id[:8]
    _assign_queue(order)
    sign_order(order)
    db.session.add(ActivityLog(actor_id=order.user_id, action="payment_recorded", detail=order.id))
    db.session.commit()
    notify(order.user_id, f"Payment successful. Your queue number is {order.queue_number}.")


def mark_cash_paid(order: Order, actor_id: int) -> None:
    if order.payment.method != "CASH" or order.payment.status != PaymentStatus.CASH_PENDING:
        raise OrderError("This order is not waiting for cash.")
    order.payment.status = PaymentStatus.CASH_PAID
    db.session.add(ActivityLog(actor_id=actor_id, action="payment_recorded", detail=order.id))
    db.session.commit()
    notify(order.user_id, "Cash payment confirmed.")


def change_status(order: Order, new_status: str, actor_id: int) -> None:
    allowed = OrderStatus.TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise OrderError(f"Cannot move an order from {order.status} to {new_status}.")
    if new_status == OrderStatus.COLLECTED:
        raise OrderError("Collection is done by scanning the QR.")
    if new_status in (OrderStatus.ACCEPTED, OrderStatus.PREPARING, OrderStatus.READY):
        paid = order.payment.status in (PaymentStatus.SUCCESS, PaymentStatus.CASH_PAID, PaymentStatus.CASH_PENDING)
        if not paid:
            raise OrderError("Payment is not in a state that allows preparation.")
    from app.models.user import utcnow

    order.status = new_status
    if new_status == OrderStatus.PREPARING:
        order.preparing_started_at = utcnow()
    if new_status in (OrderStatus.REJECTED, OrderStatus.CANCELLED):
        for item in order.items:
            restore_stock(item.food_id, item.quantity)
        _release_slot(order.pickup_slot_id)
    _refresh_queue(order)
    db.session.add(ActivityLog(actor_id=actor_id, action=f"order_{new_status.lower()}", detail=order.id))
    db.session.commit()
    notify(order.user_id, f"Order {order.queue_number or ''} is now {new_status}.")


def cancel_order(order: Order, user_id: int) -> None:
    if order.user_id != user_id:
        raise OrderError("You can only cancel your own order.")
    change_status(order, OrderStatus.CANCELLED, user_id)


def collect_with_token(token: str, stall_id: int, actor_id: int) -> Order:
    try:
        order = read_token(token)
        assert_collectable(order, stall_id)
    except QRError as exc:
        raise OrderError(str(exc)) from exc
    order.status = OrderStatus.COLLECTED
    _refresh_queue(order)
    db.session.add(ActivityLog(actor_id=actor_id, action="order_collected", detail=order.id))
    db.session.commit()
    notify(order.user_id, "Order collected. Thank you.")
    return order


def delay_flag(order: Order) -> str | None:
    """Possible delay when preparation has run longer than the items' prep times. Not a cause."""
    if order.status != OrderStatus.PREPARING or order.preparing_started_at is None:
        return None
    expected = sum(item.prep_time_minutes * item.quantity for item in order.items) or 1
    from app.models.user import utcnow

    elapsed = (utcnow() - order.preparing_started_at).total_seconds() / 60
    if elapsed > expected * 1.5:
        return f"Possible delay. Expected about {expected} min, elapsed {math.ceil(elapsed)} min."
    return None


def _assign_queue(order: Order) -> None:
    order.queue_number = f"Q{1000 + Order.query.filter(Order.queue_number.isnot(None)).count() + 1}"
    snap = queue_snapshot(order)
    db.session.add(
        QueueRecord(
            order_id=order.id,
            position=snap["position"],
            estimated_wait_minutes=snap["estimated_wait_minutes"],
        )
    )


def _refresh_queue(order: Order) -> None:
    if order.queue_record is None or order.queue_number is None:
        return
    snap = queue_snapshot(order)
    order.queue_record.position = snap["position"]
    order.queue_record.estimated_wait_minutes = snap["estimated_wait_minutes"]


def _reserve_slot(slot_id: int) -> bool:
    # One UPDATE so two students cannot both take the last space in a slot.
    result = db.session.execute(
        update(PickupSlot)
        .where(PickupSlot.id == slot_id, PickupSlot.current_orders < PickupSlot.max_orders)
        .values(current_orders=PickupSlot.current_orders + 1)
    )
    if result.rowcount != 1:
        return False
    slot = db.session.get(PickupSlot, slot_id)
    db.session.refresh(slot)
    if slot.current_orders >= slot.max_orders:
        slot.status = "FULL"
    db.session.commit()
    return True


def _release_slot(slot_id: int) -> None:
    slot = db.session.get(PickupSlot, slot_id)
    if slot and slot.current_orders > 0:
        slot.current_orders -= 1
        slot.status = "OPEN"
        db.session.commit()


def _remaining_message(food) -> str:
    if food.stock_quantity <= 0 or not food.is_available:
        return "That item is sold out."
    if food.stock_quantity == 1:
        return "Only 1 item remaining."
    return f"Only {food.stock_quantity} items remaining."
