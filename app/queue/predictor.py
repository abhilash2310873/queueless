"""Demand levels. With enough history this fits a linear model. The rows are synthetic until real orders exist."""

from datetime import datetime

from app.extensions import db
from app.models import FoodItem, Order, OrderItem, PredictionRecord


def demand_level(stall_id: int, when: datetime | None = None) -> dict:
    when = when or datetime.now()
    rows = Order.query.filter_by(stall_id=stall_id).all()
    level, note = _predict(rows, when)
    record = PredictionRecord(stall_id=stall_id, hour=when.hour, level=level, note=note)
    db.session.add(record)
    db.session.commit()
    return {"level": level, "note": note, "hour": when.hour}


def sellout_insights(stall_id: int) -> list[str]:
    """Items whose orders cluster at lunch are reported as likely to sell out then."""
    items = FoodItem.query.filter_by(stall_id=stall_id).all()
    insights = []
    for item in items:
        lines = (
            OrderItem.query.join(Order)
            .filter(OrderItem.food_id == item.id, Order.stall_id == stall_id)
            .all()
        )
        if len(lines) < 4:
            continue
        lunch = 0
        for line in lines:
            hour = line.order.created_at.hour
            minute = line.order.created_at.minute
            if hour == 12 and minute >= 45 or hour == 13 and minute <= 30:
                lunch += 1
        if lunch / len(lines) >= 0.5:
            insights.append(f"{item.name} frequently sells out between 12:45 PM and 1:30 PM.")
    return insights


def _predict(rows, when: datetime) -> tuple[str, str]:
    if len(rows) < 8:
        return "LOW", "Not enough order history to train a model yet."
    try:
        from sklearn.linear_model import LinearRegression
    except ImportError:
        return "MEDIUM", "scikit-learn is not installed, so no model was trained."
    buckets: dict[tuple[int, int], int] = {}
    for order in rows:
        key = (order.created_at.weekday(), order.created_at.hour)
        buckets[key] = buckets.get(key, 0) + 1
    features = [[day, hour] for day, hour in buckets]
    targets = list(buckets.values())
    model = LinearRegression()
    model.fit(features, targets)
    predicted = float(model.predict([[when.weekday(), when.hour]])[0])
    average = sum(targets) / len(targets)
    if predicted >= average * 1.25:
        level = "HIGH"
    elif predicted <= average * 0.75:
        level = "LOW"
    else:
        level = "MEDIUM"
    note = (
        f"LinearRegression on {len(rows)} synthetic or real orders. "
        f"Predicted count for this hour is {predicted:.1f}, average hour is {average:.1f}."
    )
    return level, note
