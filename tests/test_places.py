from app.extensions import db
from app.models import FoodCourt, PlaceStatus, Role, Stall, User

PASSWORD = "Campus@123"


def _login(client, email, password=PASSWORD):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def _make_user(email, role, student_id=None):
    user = User(
        name="Test User",
        email=email,
        role=role,
        student_id=student_id,
        email_verified=True,
    )
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


def _court_data(**extra):
    data = {
        "name": "Main Campus Food Court",
        "description": "Central lawn",
        "location": "Main campus",
        "opening_time": "08:00",
        "closing_time": "20:00",
        "owner_id": 0,
    }
    data.update(extra)
    return data


def _stall_data(court_id, **extra):
    data = {
        "food_court_id": court_id,
        "name": "Burger Hub",
        "description": "Burgers and fries",
        "location": "Counter 1",
        "contact": "9000000001",
        "opening_time": "09:00",
        "closing_time": "21:00",
    }
    data.update(extra)
    return data


def test_admin_creates_court_stall_and_owner(client):
    _make_user("admin@example.local", Role.ADMIN)
    _login(client, "admin@example.local")

    created = client.post("/admin/courts/new", data=_court_data(), follow_redirects=True)
    assert b"Food court created" in created.data
    court = FoodCourt.query.filter_by(name="Main Campus Food Court").one()
    assert court.status == PlaceStatus.CLOSED

    bad_hours = client.post(
        "/admin/courts/new",
        data=_court_data(name="Late Court", opening_time="20:00", closing_time="08:00"),
        follow_redirects=True,
    )
    assert b"Closing time must be after opening time" in bad_hours.data

    approved = client.post(f"/admin/courts/{court.id}/status", data={"status": "OPEN"}, follow_redirects=True)
    assert b"Approved and open" in approved.data
    assert db.session.get(FoodCourt, court.id).status == PlaceStatus.OPEN

    rejected = client.post(f"/admin/courts/{court.id}/status", data={"status": "NOT_A_STATUS"}, follow_redirects=True)
    assert b"not valid" in rejected.data.lower()
    assert db.session.get(FoodCourt, court.id).status == PlaceStatus.OPEN

    stall_page = client.post("/admin/stalls/new", data=_stall_data(court.id), follow_redirects=True)
    assert b"Stall created" in stall_page.data
    stall = Stall.query.filter_by(name="Burger Hub").one()
    assert stall.food_court_id == court.id
    assert stall.owner_id is None

    owner_page = client.post(
        "/admin/owners/new",
        data={"name": "Burger Admin", "email": "owner@example.local", "password": PASSWORD, "stall_id": stall.id},
        follow_redirects=True,
    )
    assert b"owner@example.local" in owner_page.data
    owner = User.query.filter_by(email="owner@example.local").one()
    assert owner.role == Role.OWNER
    assert owner.email_verified is True
    assert db.session.get(Stall, stall.id).owner_id == owner.id


def test_owner_cannot_edit_another_stall(client):
    admin = _make_user("admin@example.local", Role.ADMIN)
    _login(client, admin.email)
    client.post("/admin/courts/new", data=_court_data())
    court = FoodCourt.query.one()
    client.post("/admin/stalls/new", data=_stall_data(court.id, name="Burger Hub"))
    client.post("/admin/stalls/new", data=_stall_data(court.id, name="Juice Junction", contact="9000000002"))
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
    client.post("/auth/logout")

    _login(client, "burger@example.local")
    own = client.get(f"/owner/stalls/{burger.id}")
    assert own.status_code == 200
    assert b"Burger Hub" in own.data

    forbidden = client.get(f"/owner/stalls/{juice.id}")
    assert forbidden.status_code == 403

    blocked = client.post(
        f"/owner/stalls/{juice.id}",
        data=_stall_data(court.id, name="Taken Over", contact="111"),
    )
    assert blocked.status_code == 403
    assert db.session.get(Stall, juice.id).name == "Juice Junction"

    saved = client.post(
        f"/owner/stalls/{burger.id}",
        data={
            "name": "Burger Hub",
            "description": "Now with paneer",
            "location": "Counter 1",
            "contact": "9000000099",
            "opening_time": "09:00",
            "closing_time": "21:00",
            "status": "OPEN",
        },
        follow_redirects=True,
    )
    assert b"Stall updated" in saved.data
    assert db.session.get(Stall, burger.id).contact == "9000000099"
    assert db.session.get(Stall, burger.id).food_court_id == court.id

    assert client.get("/admin/courts").status_code == 403
    assert client.get("/admin/stalls").status_code == 403


def test_student_cannot_open_court_or_stall_admin(client):
    _make_user("student@college.edu", Role.STUDENT, student_id="CS100")
    _make_user("admin@example.local", Role.ADMIN)
    _login(client, "admin@example.local")
    client.post("/admin/courts/new", data=_court_data())
    court = FoodCourt.query.one()
    client.post("/admin/stalls/new", data=_stall_data(court.id))
    stall = Stall.query.one()
    client.post("/auth/logout")

    _login(client, "student@college.edu")
    assert client.get("/admin/courts").status_code == 403
    assert client.post(f"/admin/courts/{court.id}/status", data={"status": "OPEN"}).status_code == 403
    assert db.session.get(FoodCourt, court.id).status == PlaceStatus.CLOSED
    assert client.get(f"/owner/stalls/{stall.id}").status_code == 403
    assert client.post(f"/admin/users/{stall.id}/suspend").status_code == 403


def test_suspend_and_activate_user(client):
    admin = _make_user("admin@example.local", Role.ADMIN)
    owner = _make_user("owner@example.local", Role.OWNER)
    _login(client, admin.email)

    cannot = client.post(f"/admin/users/{admin.id}/suspend", follow_redirects=True)
    assert b"cannot suspend your own account" in cannot.data.lower()
    assert db.session.get(User, admin.id).is_suspended is False

    client.post(f"/admin/users/{owner.id}/suspend")
    assert db.session.get(User, owner.id).is_suspended is True
    client.post("/auth/logout")

    blocked = _login(client, owner.email)
    assert b"suspended" in blocked.data.lower()

    _login(client, admin.email)
    client.post(f"/admin/users/{owner.id}/activate", follow_redirects=True)
    assert db.session.get(User, owner.id).is_suspended is False
    client.post("/auth/logout")
    signed_in = _login(client, owner.email)
    assert b"signed in" in signed_in.data.lower() or b"No stall assigned" in signed_in.data
