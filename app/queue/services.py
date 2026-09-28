"""Queue position and waiting time.

Estimated wait = workload of orders ahead / active counters.
Workload is the sum of each item's preparation minutes times its quantity.
"""

import math

from app.models import Order, OrderStatus


def queue_snapshot(order: Order) -> dict:
    ahead = _orders_ahead(order)
    workload = 0
    for earlier in ahead:
        for item in earlier.items:
            workload += item.prep_time_minutes * item.quantity
    counters = max(order.stall.active_counters or 1, 1)
    wait = math.ceil(workload / counters) if workload else 0
    return {
        "queue_number": order.queue_number,
        "position": len(ahead) + 1,
        "orders_ahead": len(ahead),
        "estimated_wait_minutes": wait,
        "counters": counters,
        "workload_minutes": workload,
    }


def _orders_ahead(order: Order) -> list[Order]:
    if order.queue_number is None or order.status not in OrderStatus.ACTIVE:
        return []
    return (
        Order.query.filter(
            Order.stall_id == order.stall_id,
            Order.id != order.id,
            Order.queue_number.isnot(None),
            Order.status.in_(OrderStatus.ACTIVE),
            Order.created_at < order.created_at,
        )
        .order_by(Order.created_at.asc())
        .all()
    )


def recommend_slot(stall, slots) -> dict | None:
    """Pick the open slot with the lowest congestion score. The score is explainable, not an ML claim."""
    open_slots = [slot for slot in slots if slot.spaces_left > 0 and slot.status != "FULL"]
    if not open_slots:
        return None
    active = Order.query.filter(
        Order.stall_id == stall.id,
        Order.status.in_((OrderStatus.PENDING, OrderStatus.ACCEPTED, OrderStatus.PREPARING)),
    ).count()
    best = None
    best_score = None
    for slot in open_slots:
        fullness = slot.current_orders / slot.max_orders
        score = fullness + active * 0.05
        if best_score is None or score < best_score:
            best = slot
            best_score = score
    return {
        "slot": best,
        "reason": "Lower expected queue and preparation load.",
    }
