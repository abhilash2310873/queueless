"""Demand levels from past orders. Training rows are seeded history, not live campus data."""

from collections import Counter
from datetime import datetime

from app.extensions import db
from app.models import Order, PredictionRecord


def demand_level(stall_id: int, when: datetime | None = None) -> dict:
    when = when or datetime.now()
    hour = when.hour
    counts = Counter()
    rows = Order.query.filter_by(stall_id=stall_id).all()
    for order in rows:
        counts[order.created_at.hour] += 1
    this_hour = counts.get(hour, 0)
    if not counts:
        level = "LOW"
        note = "No order history yet."
    else:
        average = sum(counts.values()) / max(len(counts), 1)
        if this_hour >= average * 1.3 or hour in (12, 13):
            level = "HIGH" if this_hour >= average else "MEDIUM"
        elif this_hour <= average * 0.6:
            level = "LOW"
        else:
            level = "MEDIUM"
        # Lunch hours are the known peak in the seed data.
        if hour in (12, 13) and level == "LOW":
            level = "MEDIUM"
        note = f"Based on {len(rows)} historical orders. Average for an hour with orders is {average:.1f}."
    record = PredictionRecord(stall_id=stall_id, hour=hour, level=level, note=note)
    db.session.add(record)
    db.session.commit()
    return {"level": level, "note": note, "hour": hour}
