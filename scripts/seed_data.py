"""Sample campus data and five weeks of lunch-heavy order history.

Run after `flask --app run.py db upgrade`. Safe to run again: courts that
already exist are left alone. Password for every demo account is Campus@123.
"""

import sys
from datetime import datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
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

PASSWORD = "Campus@123"

COURTS = [
    ("Main Campus Food Court", "Central lawn", "Main campus", [
        ("Burger Hub", "owner@example.local", "Burger Hub Admin", [
            ("Veg Burger", "90", True, 20, True),
            ("Chicken Burger", "120", False, 15, True),
            ("French Fries", "70", True, 0, True),
            ("Paneer Burger", "110", True, 12, False),
            ("Chicken Wrap", "130", False, 10, True),
        ]),
        ("Juice Junction", "juice@example.local", "Juice Junction Admin", [
            ("Fresh Lime", "40", True, 25, True),
            ("Orange Juice", "60", True, 18, True),
            ("Mango Shake", "80", True, 14, True),
            ("Watermelon Juice", "60", True, 16, True),
        ]),
        ("Coffee House", "coffee@example.local", "Coffee House Admin", [
            ("Tea", "20", True, 40, True),
            ("Coffee", "30", True, 40, True),
            ("Cold Coffee", "70", True, 12, True),
            ("Sandwich", "80", True, 10, True),
        ]),
    ]),
    ("Engineering Food Court", "Beside the workshop", "Engineering block", [
        ("South Indian Corner", "south@example.local", "South Indian Admin", [
            ("Idli", "40", True, 30, True),
            ("Vada", "35", True, 24, True),
            ("Masala Dosa", "70", True, 18, True),
            ("Plain Dosa", "50", True, 18, True),
            ("Veg Meals", "100", True, 12, True),
        ]),
        ("Snack Station", "snacks@example.local", "Snack Station Admin", [
            ("Samosa", "20", True, 40, True),
            ("Veg Puff", "30", True, 20, True),
            ("Chicken Puff", "45", False, 15, True),
            ("French Fries", "70", True, 10, True),
        ]),
        ("Tea Point", "tea@example.local", "Tea Point Admin", [
            ("Tea", "20", True, 50, True),
            ("Ginger Tea", "25", True, 30, True),
            ("Coffee", "30", True, 30, True),
            ("Lemon Tea", "25", True, 20, True),
        ]),
    ]),
    ("Library Food Court", "Ground floor", "Library", [
        ("Quick Bites", "quick@example.local", "Quick Bites Admin", [
            ("Veg Sandwich", "70", True, 16, True),
            ("Chicken Sandwich", "90", False, 10, True),
            ("Pasta", "100", True, 8, True),
            ("Noodles", "90", True, 8, True),
        ]),
        ("Cafe Corner", "cafe@example.local", "Cafe Corner Admin", [
            ("Cappuccino", "80", True, 14, True),
            ("Latte", "90", True, 14, True),
            ("Cold Coffee", "80", True, 10, True),
            ("Brownie", "60", True, 6, False),
        ]),
    ]),
]

CATEGORIES = ["Breakfast", "Meals", "Snacks", "Fast Food", "Beverages", "Desserts", "South Indian", "North Indian"]


def _user(email, name, role, student_id=None):
    existing = User.query.filter_by(email=email).first()
    if existing:
        return existing
    account = User(name=name, email=email, role=role, student_id=student_id, email_verified=True)
    account.set_password(PASSWORD)
    db.session.add(account)
    db.session.flush()
    return account


def _history(student, stall, food, slot, start_index):
    """Weekday lunch peak, lighter evenings, fewer weekend orders."""
    start = datetime.now().replace(hour=12, minute=45, second=0, microsecond=0) - timedelta(days=35)
    made = 0
    for day in range(35):
        moment = start + timedelta(days=day)
        weekend = moment.weekday() >= 5
        lunch_orders = 1 if weekend else 6
        for n in range(lunch_orders):
            when = moment.replace(hour=12, minute=45) + timedelta(minutes=7 * n)
            _past_order(student, stall, food, slot, when, start_index + made)
            made += 1
        if not weekend:
            evening = moment.replace(hour=17, minute=15)
            _past_order(student, stall, food, slot, evening, start_index + made)
            made += 1
    return made


def _past_order(student, stall, food, slot, when, number):
    order = Order(
        user_id=student.id,
        food_court_id=stall.food_court_id,
        stall_id=stall.id,
        pickup_slot_id=slot.id,
        total=food.price,
        payment_method="CASH",
        status=OrderStatus.COLLECTED,
        queue_number=f"H{number}",
        created_at=when,
        updated_at=when,
    )
    db.session.add(order)
    db.session.flush()
    db.session.add(
        OrderItem(
            order_id=order.id,
            food_id=food.id,
            name=food.name,
            quantity=1,
            unit_price=food.price,
            prep_time_minutes=food.prep_time_minutes,
        )
    )
    db.session.add(
        Payment(order_id=order.id, amount=food.price, method="CASH", status=PaymentStatus.CASH_PAID, created_at=when)
    )


def run():
    if FoodCourt.query.filter_by(name="Engineering Food Court").first():
        print("Full seed already present.")
        return
    _user("admin@example.local", "Super Admin", Role.ADMIN)
    student = _user("student@college.edu", "Asha", Role.STUDENT, "CS1001")
    categories = {}
    for name in CATEGORIES:
        row = FoodCategory.query.filter_by(name=name).first()
        if row is None:
            row = FoodCategory(name=name, description="")
            db.session.add(row)
            db.session.flush()
        categories[name] = row
    history_index = 1000
    for court_name, description, location, stalls in COURTS:
        court = FoodCourt.query.filter_by(name=court_name).first()
        if court is None:
            court = FoodCourt(
                name=court_name,
                description=description,
                location=location,
                opening_time=time(8, 0),
                closing_time=time(21, 0),
                status=PlaceStatus.OPEN,
            )
            db.session.add(court)
            db.session.flush()
        for stall_name, email, owner_name, foods in stalls:
            owner = _user(email, owner_name, Role.OWNER)
            stall = Stall.query.filter_by(food_court_id=court.id, name=stall_name).first()
            if stall is None:
                stall = Stall(
                    food_court_id=court.id,
                    name=stall_name,
                    description=description,
                    location=location,
                    contact="9000000000",
                    owner_id=owner.id,
                    opening_time=time(9, 0),
                    closing_time=time(21, 0),
                    status=PlaceStatus.OPEN,
                    active_counters=2,
                )
                db.session.add(stall)
                db.session.flush()
                db.session.add(PickupSlot(stall_id=stall.id, start_time=time(12, 0), end_time=time(12, 15), max_orders=12))
                db.session.add(PickupSlot(stall_id=stall.id, start_time=time(12, 15), end_time=time(12, 30), max_orders=12))
                db.session.flush()
            slot = PickupSlot.query.filter_by(stall_id=stall.id).first()
            if slot is None:
                slot = PickupSlot(stall_id=stall.id, start_time=time(12, 0), end_time=time(12, 15), max_orders=12)
                db.session.add(slot)
                db.session.flush()
            category = categories["South Indian"] if "South" in stall_name else categories["Beverages"] if "Juice" in stall_name or "Tea" in stall_name or "Coffee" in stall_name or "Cafe" in stall_name else categories["Fast Food"]
            first_food = None
            for food_name, price, veg, stock, available in foods:
                food = FoodItem.query.filter_by(stall_id=stall.id, name=food_name).first()
                if food is None:
                    food = FoodItem(
                        stall_id=stall.id,
                        category_id=category.id,
                        name=food_name,
                        description="",
                        price=Decimal(price),
                        prep_time_minutes=8,
                        stock_quantity=stock,
                        is_available=available and stock > 0,
                        is_vegetarian=veg,
                    )
                    db.session.add(food)
                    db.session.flush()
                if first_food is None:
                    first_food = food
            if first_food and not Order.query.filter_by(stall_id=stall.id, status=OrderStatus.COLLECTED).first():
                history_index += _history(student, stall, first_food, slot, history_index)
    db.session.commit()
    print("Seeded 3 food courts, 8 stalls, menus, and lunch-heavy history.")
    print("student@college.edu and owner@example.local use Campus@123.")


if __name__ == "__main__":
    application = create_app()
    with application.app_context():
        run()
