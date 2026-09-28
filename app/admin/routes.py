from flask import Blueprint, render_template

from app.models import Role, User
from app.utils.decorators import roles_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/users")
@roles_required(Role.ADMIN)
def users():
    # Read-only list. Creating owners and suspending users come in a later phase.
    accounts = User.query.order_by(User.id.asc()).all()
    return render_template("admin/users.html", accounts=accounts)
