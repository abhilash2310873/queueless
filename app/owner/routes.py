from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.admin.services import PlaceError
from app.models import PlaceStatus, Role
from app.owner.forms import OwnerStallForm
from app.owner.services import get_stall_for_owner, update_owned_stall
from app.utils.decorators import roles_required

owner_bp = Blueprint("owner", __name__, url_prefix="/owner")


@owner_bp.route("/stall")
@roles_required(Role.OWNER)
def home():
    stall = current_user.owned_stall
    if stall is None:
        return render_template("owner/stall.html", stall=None, form=None)
    return redirect(url_for("owner.stall_detail", stall_id=stall.id))


@owner_bp.route("/stalls/<int:stall_id>", methods=["GET", "POST"])
@roles_required(Role.OWNER)
def stall_detail(stall_id: int):
    stall = get_stall_for_owner(current_user, stall_id)
    form = OwnerStallForm(obj=stall) if request.method == "GET" else OwnerStallForm()
    if form.validate_on_submit():
        try:
            update_owned_stall(
                current_user,
                stall,
                form.name.data,
                form.description.data,
                form.location.data,
                form.contact.data,
                form.opening_time.data,
                form.closing_time.data,
                form.status.data,
                form.image.data,
            )
        except PlaceError as exc:
            flash(str(exc), "danger")
        else:
            flash("Stall updated.", "success")
            return redirect(url_for("owner.stall_detail", stall_id=stall.id))
    return render_template("owner/stall.html", stall=stall, form=form, statuses=PlaceStatus)
