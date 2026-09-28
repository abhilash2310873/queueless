"""An owner may change their own stall. The service rejects every other stall id."""

from flask import abort

from app.extensions import db
from app.models import PlaceStatus, Stall
from app.admin.services import PlaceError, check_hours, stall_name_taken, store_image


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
