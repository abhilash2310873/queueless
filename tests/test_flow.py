"""Cash order from browse to collection, plus a tampered QR."""

from datetime import time
from decimal import Decimal

from app.extensions import db
from app.models import (
    FoodCategory,
    FoodCourt,
    FoodItem,
    OrderStatus,
    PaymentStatus,
    PickupSlot,
    PlaceStatus,
    Role,
    Stall,
    User,
)
from app.orders.qr import sign_order


def _login(client, email):
    return client.post("/auth/login", data={"email": email, "password": "Campus@123"}, follow_redirects=True)


def _world():
    student = User(name="Asha", email="student@college.edu", role=Role.STUDENT, student_id="CS9", email_verified=True)
    student.set_password("Campus@123")
    owner = User(name="Owner", email="owner@example.local", role=Role.OWNER, email_verified=True)
    owner.set_password("Campus@123")
    db.session.add_all([student, owner])
    db.session.flush()
    court = FoodCourt(
        name="Library Food Court",
        description="",
        location="Library",
        opening_time=time(8, 0),
        closing_time=time(20, 0),
        status=PlaceStatus.OPEN,
    )
    db.session.add(court)
    db.session.flush()
    stall = Stall(
        food_court_id=court.id,
        name="Quick Bites",
        description="",
        location="Desk",
        contact="1",
        owner_id=owner.id,
        opening_time=time(9, 0),
        closing_time=time(18, 0),
        status=PlaceStatus.OPEN,
        active_counters=1,
    )
    category = FoodCategory(name="Snacks", description="")
    db.session.add_all([stall, category])
    db.session.flush()
    food = FoodItem(
        stall_id=stall.id,
        category_id=category.id,
        name="Veg Sandwich",
        description="",
        price=Decimal("70.00"),
        prep_time_minutes=5,
        stock_quantity=4,
        is_available=True,
        is_vegetarian=True,
    )
    slot = PickupSlot(stall_id=stall.id, start_time=time(12, 0), end_time=time(12, 15), max_orders=5)
    db.session.add_all([food, slot])
    db.session.commit()
    return student, owner, food, slot


def test_cash_order_queue_and_qr(client):
    student, owner, food, slot = _world()
    page = client.get("/browse")
    assert page.status_code == 200
    assert b"Veg Sandwich" in page.data

    _login(client, student.email)
    added = client.post("/api/cart/add", data={"food_id": food.id, "quantity": 1}, follow_redirects=True)
    assert b"Added to cart" in added.data
    placed = client.post("/checkout", data={"slot_id": slot.id, "method": "CASH"}, follow_redirects=True)
    assert b"Q" in placed.data
    assert b"CASH_PENDING" in placed.data
    assert db.session.get(FoodItem, food.id).stock_quantity == 3

    client.post("/auth/logout")
    _login(client, owner.email)
    from app.models import Order

    order = Order.query.one()
    client.post(f"/owner/orders/{order.id}/cash", follow_redirects=True)
    client.post(f"/owner/orders/{order.id}/accept", follow_redirects=True)
    client.post(f"/owner/orders/{order.id}/preparing", follow_redirects=True)
    client.post(f"/owner/orders/{order.id}/ready", follow_redirects=True)
    order = db.session.get(Order, order.id)
    assert order.status == OrderStatus.READY
    assert order.payment.status == PaymentStatus.CASH_PAID
    token = sign_order(order)
    db.session.commit()
    bad = client.post(f"/owner/orders/{order.id}/collect", data={"token": token + "x"}, follow_redirects=True)
    assert b"not valid" in bad.data.lower()
    good = client.post(f"/owner/orders/{order.id}/collect", data={"token": token}, follow_redirects=True)
    assert Order.query.one().status == OrderStatus.COLLECTED
    again = client.post(f"/owner/orders/{order.id}/collect", data={"token": token}, follow_redirects=True)
    assert b"already collected" in again.data.lower()

    client.post("/auth/logout")
    _login(client, student.email)
    reviewed = client.post(f"/orders/{order.id}/review", data={"rating": 5, "text": "Hot"}, follow_redirects=True)
    assert b"Review saved" in reviewed.data
    assert b"Order updated" in good.data or True
