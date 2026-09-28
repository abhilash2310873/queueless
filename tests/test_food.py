from decimal import Decimal

from app.extensions import db
from app.models import FoodCategory, FoodCourt, FoodItem, Role, Stall, User

PASSWORD = "Campus@123"


def _login(client, email, password=PASSWORD):
    return client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def _user(email, role, student_id=None):
    account = User(name="Test User", email=email, role=role, student_id=student_id, email_verified=True)
    account.set_password(PASSWORD)
    db.session.add(account)
    db.session.commit()
    return account


def _setup_two_stalls(client):
    """Admin, two approved stalls, two owners, and a Fast Food category."""
    _user("admin@example.local", Role.ADMIN)
    _login(client, "admin@example.local")
    client.post(
        "/admin/courts/new",
        data={
            "name": "Main Campus Food Court",
            "description": "",
            "location": "Main campus",
            "opening_time": "08:00",
            "closing_time": "20:00",
            "owner_id": 0,
        },
    )
    court = FoodCourt.query.one()
    client.post(f"/admin/courts/{court.id}/status", data={"status": "OPEN"})
    client.post(
        "/admin/stalls/new",
        data={
            "food_court_id": court.id,
            "name": "Burger Hub",
            "description": "",
            "location": "Counter 1",
            "contact": "9000000001",
            "opening_time": "09:00",
            "closing_time": "21:00",
        },
    )
    client.post(
        "/admin/stalls/new",
        data={
            "food_court_id": court.id,
            "name": "Juice Junction",
            "description": "",
            "location": "Counter 2",
            "contact": "9000000002",
            "opening_time": "09:00",
            "closing_time": "21:00",
        },
    )
    burger = Stall.query.filter_by(name="Burger Hub").one()
    juice = Stall.query.filter_by(name="Juice Junction").one()
    client.post(
        "/admin/owners/new",
        data={"name": "Burger Admin", "email": "burger@example.local", "password": PASSWORD, "stall_id": burger.id},
    )
    client.post(
        "/admin/owners/new",
        data={"name": "Juice Admin", "email": "juice@example.local", "password": PASSWORD, "stall_id": juice.id},
    )
    client.post("/admin/categories", data={"name": "Fast Food", "description": "Burgers and wraps"})
    client.post("/auth/logout")
    return burger, juice, FoodCategory.query.filter_by(name="Fast Food").one()


def _food_data(category_id, **extra):
    data = {
        "category_id": category_id,
        "name": "Chicken Burger",
        "description": "Grilled chicken patty",
        "price": "120.00",
        "prep_time_minutes": "8",
        "stock_quantity": "15",
        "is_vegetarian": "",
        "is_available": "y",
    }
    data.update(extra)
    return data


def test_admin_manages_categories(client):
    _user("admin@example.local", Role.ADMIN)
    _login(client, "admin@example.local")
    created = client.post("/admin/categories", data={"name": "Breakfast", "description": "Morning"}, follow_redirects=True)
    assert b"Category saved" in created.data
    category = FoodCategory.query.filter_by(name="Breakfast").one()

    updated = client.post(
        f"/admin/categories/{category.id}/edit",
        data={"name": "Breakfast", "description": "Until 11am"},
        follow_redirects=True,
    )
    assert b"Category updated" in updated.data
    assert FoodCategory.query.one().description == "Until 11am"

    _user("student@college.edu", Role.STUDENT, student_id="CS200")
    client.post("/auth/logout")
    _login(client, "student@college.edu")
    assert client.get("/admin/categories").status_code == 403
    assert client.post("/admin/categories", data={"name": "Snacks"}).status_code == 403
    assert FoodCategory.query.count() == 1


def test_owner_creates_updates_and_toggles_food(client):
    burger, juice, category = _setup_two_stalls(client)
    _login(client, "burger@example.local")

    created = client.post(
        f"/owner/stalls/{burger.id}/menu/new",
        data=_food_data(category.id),
        follow_redirects=True,
    )
    assert b"Food added" in created.data
    item = FoodItem.query.filter_by(name="Chicken Burger").one()
    assert item.stall_id == burger.id
    assert item.price == Decimal("120.00")
    assert item.prep_time_minutes == 8
    assert item.stock_quantity == 15
    assert item.is_available is True
    assert item.is_vegetarian is False
    assert item.availability_label == "AVAILABLE"

    zero = client.post(
        f"/owner/stalls/{burger.id}/menu/new",
        data=_food_data(category.id, name="Free Item", price="0"),
        follow_redirects=True,
    )
    assert FoodItem.query.filter_by(name="Free Item").first() is None
    assert b"Free Item" in zero.data

    negative = client.post(
        f"/owner/stalls/{burger.id}/menu/new",
        data=_food_data(category.id, name="Bad Stock", stock_quantity="-1"),
        follow_redirects=True,
    )
    assert FoodItem.query.filter_by(name="Bad Stock").first() is None

    fries = client.post(
        f"/owner/stalls/{burger.id}/menu/new",
        data=_food_data(category.id, name="French Fries", price="70", prep_time_minutes="5", is_vegetarian="y"),
        follow_redirects=True,
    )
    assert b"Food added" in fries.data
    fries_item = FoodItem.query.filter_by(name="French Fries").one()

    hidden = client.post(
        f"/owner/stalls/{burger.id}/menu/{fries_item.id}/availability",
        data={"is_available": "0"},
        follow_redirects=True,
    )
    assert b"Marked unavailable" in hidden.data
    fries_item = db.session.get(FoodItem, fries_item.id)
    assert fries_item.is_available is False
    assert fries_item.availability_label == "CURRENTLY UNAVAILABLE"

    sold = client.post(
        f"/owner/stalls/{burger.id}/menu/{item.id}/edit",
        data=_food_data(category.id, stock_quantity="0"),
        follow_redirects=True,
    )
    assert b"Food updated" in sold.data
    sold_item = db.session.get(FoodItem, item.id)
    assert sold_item.stock_quantity == 0
    assert sold_item.availability_label == "SOLD OUT"

    page = client.get("/admin/food")
    assert page.status_code == 403
    client.post("/auth/logout")
    _login(client, "admin@example.local")
    all_food = client.get("/admin/food")
    assert all_food.status_code == 200
    assert b"Chicken Burger" in all_food.data
    assert b"French Fries" in all_food.data
    assert b"CURRENTLY UNAVAILABLE" in all_food.data
    assert b"SOLD OUT" in all_food.data


def test_owner_cannot_change_another_stall_food(client):
    burger, juice, category = _setup_two_stalls(client)
    _login(client, "burger@example.local")
    client.post(f"/owner/stalls/{burger.id}/menu/new", data=_food_data(category.id))
    burger_item = FoodItem.query.filter_by(name="Chicken Burger").one()
    client.post("/auth/logout")

    _login(client, "juice@example.local")
    assert client.get(f"/owner/stalls/{burger.id}/menu").status_code == 403
    assert client.get(f"/owner/stalls/{juice.id}/menu/{burger_item.id}/edit").status_code == 403
    stolen = client.post(
        f"/owner/stalls/{juice.id}/menu/{burger_item.id}/edit",
        data=_food_data(category.id, name="Stolen Burger", price="1"),
    )
    assert stolen.status_code == 403
    assert FoodItem.query.filter_by(name="Chicken Burger").one().price == Decimal("120.00")

    toggle = client.post(
        f"/owner/stalls/{burger.id}/menu/{burger_item.id}/availability",
        data={"is_available": "0"},
    )
    assert toggle.status_code == 403
    assert db.session.get(FoodItem, burger_item.id).is_available is True

    client.post(
        f"/owner/stalls/{juice.id}/menu/new",
        data=_food_data(category.id, name="Fresh Lime", price="40", is_vegetarian="y"),
    )
    juice_item = FoodItem.query.filter_by(name="Fresh Lime").one()
    delete = client.post(f"/owner/stalls/{burger.id}/menu/{juice_item.id}/delete")
    assert delete.status_code == 403
    assert db.session.get(FoodItem, juice_item.id) is not None
