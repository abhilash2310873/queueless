from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.admin.services import PlaceError
from app.models import FoodCategory, PlaceStatus, Role
from app.owner.forms import FoodItemForm, OwnerStallForm
from app.owner.services import (
    FoodError,
    create_food_item,
    delete_food_item,
    get_food_for_owner,
    get_stall_for_owner,
    set_food_availability,
    update_food_item,
    update_owned_stall,
)
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


def _category_choices():
    return [(row.id, row.name) for row in FoodCategory.query.order_by(FoodCategory.name.asc()).all()]


@owner_bp.route("/stalls/<int:stall_id>/menu")
@roles_required(Role.OWNER)
def menu(stall_id: int):
    stall = get_stall_for_owner(current_user, stall_id)
    return render_template("owner/menu.html", stall=stall, items=stall.food_items)


@owner_bp.route("/stalls/<int:stall_id>/menu/new", methods=["GET", "POST"])
@roles_required(Role.OWNER)
def new_food(stall_id: int):
    stall = get_stall_for_owner(current_user, stall_id)
    form = FoodItemForm()
    form.category_id.choices = _category_choices()
    if not form.category_id.choices:
        flash("Ask an admin to create a food category first.", "warning")
        return redirect(url_for("owner.menu", stall_id=stall.id))
    if form.validate_on_submit():
        try:
            create_food_item(
                current_user,
                stall,
                form.category_id.data,
                form.name.data,
                form.description.data,
                form.price.data,
                form.prep_time_minutes.data,
                form.stock_quantity.data,
                form.is_available.data,
                form.is_vegetarian.data,
                form.image.data,
            )
        except (FoodError, PlaceError) as exc:
            flash(str(exc), "danger")
        else:
            flash("Food added to the menu.", "success")
            return redirect(url_for("owner.menu", stall_id=stall.id))
    return render_template("owner/food_form.html", form=form, stall=stall, heading="New food")


@owner_bp.route("/stalls/<int:stall_id>/menu/<int:food_id>/edit", methods=["GET", "POST"])
@roles_required(Role.OWNER)
def edit_food(stall_id: int, food_id: int):
    stall = get_stall_for_owner(current_user, stall_id)
    item = get_food_for_owner(current_user, food_id)
    if item.stall_id != stall.id:
        abort(403)
    form = FoodItemForm(obj=item) if request.method == "GET" else FoodItemForm()
    form.category_id.choices = _category_choices()
    if request.method == "GET":
        form.category_id.data = item.category_id
        form.is_available.data = item.is_available
        form.is_vegetarian.data = item.is_vegetarian
    if form.validate_on_submit():
        try:
            update_food_item(
                current_user,
                item,
                form.category_id.data,
                form.name.data,
                form.description.data,
                form.price.data,
                form.prep_time_minutes.data,
                form.stock_quantity.data,
                form.is_available.data,
                form.is_vegetarian.data,
                form.image.data,
            )
        except (FoodError, PlaceError) as exc:
            flash(str(exc), "danger")
        else:
            flash("Food updated.", "success")
            return redirect(url_for("owner.menu", stall_id=stall.id))
    return render_template("owner/food_form.html", form=form, stall=stall, heading="Edit food", item=item)


@owner_bp.route("/stalls/<int:stall_id>/menu/<int:food_id>/availability", methods=["POST"])
@roles_required(Role.OWNER)
def food_availability(stall_id: int, food_id: int):
    stall = get_stall_for_owner(current_user, stall_id)
    item = get_food_for_owner(current_user, food_id)
    if item.stall_id != stall.id:
        abort(403)
    available = request.form.get("is_available") == "1"
    set_food_availability(current_user, item, available)
    flash("Marked available." if available else "Marked unavailable.", "success")
    return redirect(url_for("owner.menu", stall_id=stall.id))


@owner_bp.route("/stalls/<int:stall_id>/menu/<int:food_id>/delete", methods=["POST"])
@roles_required(Role.OWNER)
def remove_food(stall_id: int, food_id: int):
    stall = get_stall_for_owner(current_user, stall_id)
    item = get_food_for_owner(current_user, food_id)
    if item.stall_id != stall.id:
        abort(403)
    delete_food_item(current_user, item)
    flash("Food removed from the menu.", "success")
    return redirect(url_for("owner.menu", stall_id=stall.id))
