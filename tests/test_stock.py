import threading
from datetime import time
from decimal import Decimal

import pytest
from sqlalchemy.pool import NullPool

from app import create_app
from app.extensions import db
from app.models import FoodCategory, FoodCourt, FoodItem, PlaceStatus, Role, Stall, User
from app.utils.stock import StockError, deduct_stock, restore_stock


def _food(stock, available=True):
    owner = User(name="Owner", email="owner@example.local", role=Role.OWNER, email_verified=True)
    owner.set_password("Campus@123")
    db.session.add(owner)
    db.session.flush()
    court = FoodCourt(
        name="Main Campus Food Court",
        description="",
        location="Main campus",
        opening_time=time(8, 0),
        closing_time=time(20, 0),
        status=PlaceStatus.OPEN,
    )
    db.session.add(court)
    db.session.flush()
    stall = Stall(
        food_court_id=court.id,
        name="Burger Hub",
        description="",
        location="Counter 1",
        contact="9000000001",
        owner_id=owner.id,
        opening_time=time(9, 0),
        closing_time=time(21, 0),
        status=PlaceStatus.OPEN,
    )
    category = FoodCategory(name="Fast Food", description="")
    db.session.add_all([stall, category])
    db.session.flush()
    item = FoodItem(
        stall_id=stall.id,
        category_id=category.id,
        name="Chicken Burger",
        description="",
        price=Decimal("120.00"),
        prep_time_minutes=8,
        stock_quantity=stock,
        is_available=available,
        is_vegetarian=False,
    )
    db.session.add(item)
    db.session.commit()
    return item.id


def test_deduct_stock_and_sell_out(app):
    food_id = _food(3)
    assert deduct_stock(food_id, 2) == 1
    item = db.session.get(FoodItem, food_id)
    assert item.stock_quantity == 1
    assert item.is_available is True

    with pytest.raises(StockError, match="Only 1 item remaining"):
        deduct_stock(food_id, 2)
    item = db.session.get(FoodItem, food_id)
    assert item.stock_quantity == 1

    assert deduct_stock(food_id, 1) == 0
    item = db.session.get(FoodItem, food_id)
    assert item.stock_quantity == 0
    assert item.is_available is False
    assert item.availability_label == "SOLD OUT"


def test_negative_quantity_is_rejected(app):
    food_id = _food(4)
    with pytest.raises(StockError):
        deduct_stock(food_id, 0)
    assert db.session.get(FoodItem, food_id).stock_quantity == 4


def test_unavailable_item_is_not_deducted(app):
    food_id = _food(5, available=False)
    with pytest.raises(StockError, match="sold out"):
        deduct_stock(food_id, 1)
    assert db.session.get(FoodItem, food_id).stock_quantity == 5


def test_restore_does_not_mark_available(app):
    food_id = _food(1)
    deduct_stock(food_id, 1)
    assert restore_stock(food_id, 2) == 2
    item = db.session.get(FoodItem, food_id)
    assert item.stock_quantity == 2
    assert item.is_available is False


def test_two_requests_cannot_take_the_last_item(tmp_path):
    from config import TestingConfig

    uri = "sqlite:///" + (tmp_path / "race.db").as_posix()
    original_uri = TestingConfig.SQLALCHEMY_DATABASE_URI
    original_options = TestingConfig.SQLALCHEMY_ENGINE_OPTIONS
    # Set this before create_app so both threads share the file database, not the memory one.
    TestingConfig.SQLALCHEMY_DATABASE_URI = uri
    TestingConfig.SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False, "timeout": 10},
        "poolclass": NullPool,
    }
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        food_id = _food(1)
        db.session.remove()

    barrier = threading.Barrier(2)
    results = []

    def attempt():
        with app.app_context():
            barrier.wait()
            try:
                deduct_stock(food_id, 1)
                results.append("ok")
            except StockError:
                results.append("no")
            finally:
                db.session.remove()

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == ["no", "ok"]
    with app.app_context():
        item = db.session.get(FoodItem, food_id)
        assert item.stock_quantity == 0
        assert item.is_available is False
        db.session.remove()
        db.drop_all()
    TestingConfig.SQLALCHEMY_DATABASE_URI = original_uri
    TestingConfig.SQLALCHEMY_ENGINE_OPTIONS = original_options
