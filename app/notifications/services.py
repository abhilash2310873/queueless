"""In-app messages. Email is not used for these."""

from app.extensions import db
from app.models import Notification


def notify(user_id: int, message: str) -> None:
    db.session.add(Notification(user_id=user_id, message=message))
    db.session.commit()
