"""Create and update courts, stalls, and the owner accounts linked to them."""

from app.extensions import db
from app.models import FoodCategory, FoodCourt, PlaceStatus, Role, Stall, User
from app.utils.uploads import UploadError, save_image


class PlaceError(Exception):
    """A court, stall, or owner problem we can show to the admin."""


def create_food_court(name, description, location, opening_time, closing_time, owner_id, image_file=None):
    check_hours(opening_time, closing_time)
    name = name.strip()
    if FoodCourt.query.filter_by(name=name).first():
        raise PlaceError("A food court with that name already exists.")
    court = FoodCourt(
        name=name,
        description=(description or "").strip(),
        location=location.strip(),
        opening_time=opening_time,
        closing_time=closing_time,
        status=PlaceStatus.CLOSED,
        owner_id=_court_owner_id(owner_id),
        image_path=store_image(image_file),
    )
    db.session.add(court)
    db.session.commit()
    return court


def update_food_court(court, name, description, location, opening_time, closing_time, owner_id, image_file=None):
    check_hours(opening_time, closing_time)
    name = name.strip()
    taken = FoodCourt.query.filter(FoodCourt.name == name, FoodCourt.id != court.id).first()
    if taken:
        raise PlaceError("A food court with that name already exists.")
    court.name = name
    court.description = (description or "").strip()
    court.location = location.strip()
    court.opening_time = opening_time
    court.closing_time = closing_time
    court.owner_id = _court_owner_id(owner_id)
    image = store_image(image_file)
    if image:
        court.image_path = image
    db.session.commit()
    return court


def set_place_status(place, status: str):
    """Approve sets OPEN. Reject sets CLOSED. The third value is a temporary close."""
    if status not in PlaceStatus.CHOICES:
        raise PlaceError("That status is not valid.")
    place.status = status
    db.session.commit()


def create_stall(food_court_id, name, description, location, contact, opening_time, closing_time, image_file=None):
    court = db.session.get(FoodCourt, food_court_id)
    if court is None:
        raise PlaceError("Choose a food court.")
    check_hours(opening_time, closing_time)
    name = name.strip()
    if stall_name_taken(court.id, name):
        raise PlaceError("That stall name is already used in this food court.")
    stall = Stall(
        food_court_id=court.id,
        name=name,
        description=(description or "").strip(),
        location=location.strip(),
        contact=contact.strip(),
        opening_time=opening_time,
        closing_time=closing_time,
        status=PlaceStatus.CLOSED,
        image_path=store_image(image_file),
    )
    db.session.add(stall)
    db.session.commit()
    return stall


def update_stall(stall, food_court_id, name, description, location, contact, opening_time, closing_time, image_file=None):
    court = db.session.get(FoodCourt, food_court_id)
    if court is None:
        raise PlaceError("Choose a food court.")
    check_hours(opening_time, closing_time)
    name = name.strip()
    if stall_name_taken(court.id, name, ignore_id=stall.id):
        raise PlaceError("That stall name is already used in this food court.")
    stall.food_court_id = court.id
    stall.name = name
    stall.description = (description or "").strip()
    stall.location = location.strip()
    stall.contact = contact.strip()
    stall.opening_time = opening_time
    stall.closing_time = closing_time
    image = store_image(image_file)
    if image:
        stall.image_path = image
    db.session.commit()
    return stall


def create_owner(name, email, password, stall_id) -> User:
    """Staff accounts are created by an admin, so the college-email rule does not apply."""
    email = email.strip().lower()
    stall = db.session.get(Stall, stall_id)
    if stall is None:
        raise PlaceError("Choose a stall.")
    if stall.owner_id is not None:
        raise PlaceError("That stall already has an owner.")
    if len(password) < 8:
        raise PlaceError("Password must be at least 8 characters.")
    if User.query.filter_by(email=email).first():
        raise PlaceError("An account with that email already exists.")
    owner = User(name=name.strip(), email=email, role=Role.OWNER, email_verified=True)
    owner.set_password(password)
    db.session.add(owner)
    db.session.flush()
    stall.owner_id = owner.id
    db.session.commit()
    return owner


def set_suspended(actor: User, account: User, suspended: bool) -> None:
    if suspended and actor.id == account.id:
        raise PlaceError("You cannot suspend your own account.")
    account.is_suspended = suspended
    db.session.commit()


def _court_owner_id(owner_id):
    if not owner_id:
        return None
    owner = db.session.get(User, int(owner_id))
    if owner is None or owner.role != Role.OWNER:
        raise PlaceError("The court owner must be an owner account.")
    return owner.id


def stall_name_taken(court_id, name, ignore_id=None) -> bool:
    query = Stall.query.filter_by(food_court_id=court_id, name=name)
    if ignore_id is not None:
        query = query.filter(Stall.id != ignore_id)
    return query.first() is not None


def check_hours(opening_time, closing_time) -> None:
    if opening_time >= closing_time:
        raise PlaceError("Closing time must be after opening time.")


def store_image(file_storage):
    try:
        return save_image(file_storage)
    except UploadError as exc:
        raise PlaceError(str(exc)) from exc


def create_category(name, description="") -> FoodCategory:
    name = name.strip()
    if not name:
        raise PlaceError("Enter a category name.")
    if FoodCategory.query.filter_by(name=name).first():
        raise PlaceError("That category already exists.")
    category = FoodCategory(name=name, description=(description or "").strip())
    db.session.add(category)
    db.session.commit()
    return category


def update_category(category: FoodCategory, name, description="") -> FoodCategory:
    name = name.strip()
    if not name:
        raise PlaceError("Enter a category name.")
    taken = FoodCategory.query.filter(FoodCategory.name == name, FoodCategory.id != category.id).first()
    if taken:
        raise PlaceError("That category already exists.")
    category.name = name
    category.description = (description or "").strip()
    db.session.commit()
    return category


def delete_category(category: FoodCategory) -> None:
    if category.food_items:
        raise PlaceError("Remove or recategorise the food in this category first.")
    db.session.delete(category)
    db.session.commit()
