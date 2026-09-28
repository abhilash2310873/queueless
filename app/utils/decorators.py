"""Role checks. Hiding a link is not enough; the view itself must refuse."""

from functools import wraps

from flask import abort
from flask_login import current_user

from app.extensions import login_manager


def roles_required(*roles: str):
    """Signed-out users go to the login page. The wrong role gets 403."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator
