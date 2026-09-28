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

# The login page blueprint is added in the authentication phase.
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(_user_id: str):
    """Turn a session user id into a user. Accounts do not exist yet, so this stays anonymous."""
    return None
