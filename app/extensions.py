"""Shared Flask extensions. Created here so models and routes can import them."""

from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()

login_manager.login_view = "auth.login"
login_manager.login_message = "Log in to continue."
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id: str):
    """Load the user stored in the session. Unknown ids stay signed out."""
    from app.models import User

    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        # A damaged session cookie should sign the user out, not crash the page.
        return None
