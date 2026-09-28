"""An owner may change their own stall and its menu. Other stall ids return 403."""

from decimal import Decimal, InvalidOperation

from flask import abort

from app.extensions import db
from app.models import FoodCategory, FoodItem, PlaceStatus, Stall
from app.admin.services import PlaceError, check_hours, stall_name_taken, store_image


class FoodError(Exception):
    """A menu problem we can show to the stall owner."""


def get_stall_for_owner(user, stall_id: int) -> Stall:
    """Return the stall only when this user is its owner.

    A missing id and someone else's stall both return 403, so an owner cannot
    tell which other stall numbers exist.
    """
    stall = db.session.get(Stall, stall_id)
    if stall is None or stall.owner_id != user.id:
        abort(403)
    return stall


def update_owned_stall(user, stall, name, description, location, contact, opening_time, closing_time, status, image_file=None):
    if stall.owner_id != user.id:
        abort(403)
    if status not in PlaceStatus.CHOICES:
        raise PlaceError("That status is not valid.")
    check_hours(opening_time, closing_time)
    name = name.strip()
    if stall_name_taken(stall.food_court_id, name, ignore_id=stall.id):
        raise PlaceError("That stall name is already used in this food court.")
    # food_court_id and owner_id are intentionally not updated here.
    stall.name = name
    stall.description = (description or "").strip()
    stall.location = location.strip()
    stall.contact = contact.strip()
    stall.opening_time = opening_time
    stall.closing_time = closing_time
    stall.status = status
    image = store_image(image_file)
    if image:
        stall.image_path = image
    db.session.commit()
    return stall


def get_food_for_owner(user, food_id: int) -> FoodItem:
    """Load a menu item only if it belongs to this owner's stall."""
    item = db.session.get(FoodItem, food_id)
    if item is None or item.stall.owner_id != user.id:
        abort(403)
    return item


def create_food_item(
    user,
    stall,
    category_id,
    name,
    description,
    price,
    prep_time_minutes,
    stock_quantity,
    is_available,
    is_vegetarian,
    image_file=None,
) -> FoodItem:
    if stall.owner_id != user.id:
        abort(403)
    payload = _validated_food(
        stall.id, category_id, name, description, price, prep_time_minutes, stock_quantity
    )
    item = FoodItem(
        stall_id=stall.id,
        category_id=payload["category_id"],
        name=payload["name"],
        description=payload["description"],
        price=payload["price"],
        prep_time_minutes=payload["prep_time_minutes"],
        stock_quantity=payload["stock_quantity"],
        is_available=bool(is_available),
        is_vegetarian=bool(is_vegetarian),
        image_path=store_image(image_file),
    )
    db.session.add(item)
    db.session.commit()
    return item


def update_food_item(
    user,
    item,
    category_id,
    name,
    description,
    price,
    prep_time_minutes,
    stock_quantity,
    is_available,
    is_vegetarian,
    image_file=None,
) -> FoodItem:
    if item.stall.owner_id != user.id:
        abort(403)
    payload = _validated_food(
        item.stall_id, category_id, name, description, price, prep_time_minutes, stock_quantity, ignore_id=item.id
    )
    item.category_id = payload["category_id"]
    item.name = payload["name"]
    item.description = payload["description"]
    item.price = payload["price"]
    item.prep_time_minutes = payload["prep_time_minutes"]
    item.stock_quantity = payload["stock_quantity"]
    item.is_available = bool(is_available)
    item.is_vegetarian = bool(is_vegetarian)
    image = store_image(image_file)
    if image:
        item.image_path = image
    db.session.commit()
    return item


def set_food_availability(user, item: FoodItem, is_available: bool) -> FoodItem:
    if item.stall.owner_id != user.id:
        abort(403)
    item.is_available = bool(is_available)
    db.session.commit()
    return item


def delete_food_item(user, item: FoodItem) -> None:
    if item.stall.owner_id != user.id:
        abort(403)
    db.session.delete(item)
    db.session.commit()


def _validated_food(stall_id, category_id, name, description, price, prep_time_minutes, stock_quantity, ignore_id=None):
    category = db.session.get(FoodCategory, int(category_id or 0))
    if category is None:
        raise FoodError("Choose a food category.")
    name = (name or "").strip()
    if not name:
        raise FoodError("Enter a food name.")
    taken = FoodItem.query.filter_by(stall_id=stall_id, name=name)
    if ignore_id is not None:
        taken = taken.filter(FoodItem.id != ignore_id)
    if taken.first():
        raise FoodError("That food name is already on this stall's menu.")
    try:
        amount = Decimal(str(price))
    except (InvalidOperation, TypeError):
        raise FoodError("Enter a valid price.") from None
    if amount <= 0:
        raise FoodError("Price must be greater than zero.")
    try:
        prep = int(prep_time_minutes)
        stock = int(stock_quantity)
    except (TypeError, ValueError):
        raise FoodError("Preparation time and stock must be whole numbers.") from None
    if prep < 1:
        raise FoodError("Preparation time must be at least 1 minute.")
    if stock < 0:
        raise FoodError("Stock cannot be negative.")
    return {
        "category_id": category.id,
        "name": name,
        "description": (description or "").strip(),
        "price": amount.quantize(Decimal("0.01")),
        "prep_time_minutes": prep,
        "stock_quantity": stock,
    }
