"""Development data. Run after `flask db upgrade`. Safe to run more than once."""

from datetime import datetime, time, timedelta
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import (
    FoodCategory,
    FoodCourt,
    FoodItem,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentStatus,
    PickupSlot,
    PlaceStatus,
    Role,
    Stall,
    User,
)


def run():
    if User.query.filter_by(email="student@college.edu").first():
        print("Seed data already present.")
        return
    student = User(name="Asha", email="student@college.edu", role=Role.STUDENT, student_id="CS1001", email_verified=True)
    student.set_password("Campus@123")
    owner = User(name="Burger Hub Admin", email="owner@example.local", role=Role.OWNER, email_verified=True)
    owner.set_password("Campus@123")
    admin = User.query.filter_by(email="admin@example.local").first()
    if admin is None:
        admin = User(name="Super Admin", email="admin@example.local", role=Role.ADMIN, email_verified=True)
        admin.set_password("Campus@123")
        db.session.add(admin)
    db.session.add_all([student, owner])
    db.session.flush()
    court = FoodCourt(
        name="Main Campus Food Court",
        description="Central lawn",
        location="Main campus",
        opening_time=time(8, 0),
        closing_time=time(21, 0),
        status=PlaceStatus.OPEN,
    )
    db.session.add(court)
    db.session.flush()
    stall = Stall(
        food_court_id=court.id,
        name="Burger Hub",
        description="Burgers",
        location="Counter 1",
        contact="9000000001",
        owner_id=owner.id,
        opening_time=time(9, 0),
        closing_time=time(21, 0),
        status=PlaceStatus.OPEN,
        active_counters=2,
    )
    category = FoodCategory(name="Fast Food", description="Burgers and fries")
    db.session.add_all([stall, category])
    db.session.flush()
    food = FoodItem(
        stall_id=stall.id,
        category_id=category.id,
        name="Chicken Burger",
        description="Grilled",
        price=Decimal("120.00"),
        prep_time_minutes=8,
        stock_quantity=20,
        is_available=True,
        is_vegetarian=False,
    )
    slot = PickupSlot(stall_id=stall.id, start_time=time(12, 0), end_time=time(12, 15), max_orders=10)
    db.session.add_all([food, slot])
    db.session.flush()
    start = datetime.now().replace(hour=12, minute=30, second=0, microsecond=0) - timedelta(days=28)
    for day in range(28):
        moment = start + timedelta(days=day)
        if moment.weekday() >= 5:
            continue
        order = Order(
            user_id=student.id,
            food_court_id=court.id,
            stall_id=stall.id,
            pickup_slot_id=slot.id,
            total=Decimal("120.00"),
            payment_method="CASH",
            status=OrderStatus.COLLECTED,
            queue_number=f"H{1000+day}",
            created_at=moment,
        )
        db.session.add(order)
        db.session.flush()
        db.session.add(OrderItem(order_id=order.id, food_id=food.id, name=food.name, quantity=1, unit_price=food.price, prep_time_minutes=8))
        db.session.add(Payment(order_id=order.id, amount=order.total, method="CASH", status=PaymentStatus.CASH_PAID))
    db.session.commit()
    print("Seeded student@college.edu, owner@example.local, Burger Hub. Password Campus@123.")


if __name__ == "__main__":
    application = create_app()
    with application.app_context():
        run()
