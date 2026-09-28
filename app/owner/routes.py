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


@owner_bp.route("/orders")
@roles_required(Role.OWNER)
def orders():
    stall = current_user.owned_stall
    rows = []
    if stall is not None:
        from app.models import Order

        rows = Order.query.filter_by(stall_id=stall.id).order_by(Order.created_at.desc()).all()
    from app.analytics.services import owner_summary
    from app.queue.predictor import demand_level

    summary = owner_summary(stall) if stall else None
    demand = demand_level(stall.id) if stall else None
    return render_template("owner/orders.html", stall=stall, orders=rows, summary=summary, demand=demand)


@owner_bp.route("/orders/<order_id>/<action>", methods=["POST"])
@roles_required(Role.OWNER)
def order_action(order_id: str, action: str):
    from app.extensions import db
    from app.models import Order, OrderStatus
    from app.orders.services import OrderError, change_status, collect_with_token, mark_cash_paid

    stall = current_user.owned_stall
    order = db.session.get(Order, order_id)
    if stall is None or order is None or order.stall_id != stall.id:
        abort(403)
    mapping = {
        "accept": OrderStatus.ACCEPTED,
        "preparing": OrderStatus.PREPARING,
        "ready": OrderStatus.READY,
        "reject": OrderStatus.REJECTED,
    }
    try:
        if action == "cash":
            mark_cash_paid(order, current_user.id)
        elif action == "collect":
            collect_with_token(request.form.get("token", ""), stall.id, current_user.id)
        elif action in mapping:
            change_status(order, mapping[action], current_user.id)
        else:
            abort(404)
    except OrderError as exc:
        flash(str(exc), "danger")
    else:
        flash("Order updated.", "success")
    return redirect(url_for("owner.orders"))


@owner_bp.route("/slots", methods=["POST"])
@roles_required(Role.OWNER)
def add_slot():
    from datetime import datetime

    from app.extensions import db
    from app.models import PickupSlot

    stall = current_user.owned_stall
    if stall is None:
        abort(403)
    start = datetime.strptime(request.form.get("start_time", ""), "%H:%M").time()
    end = datetime.strptime(request.form.get("end_time", ""), "%H:%M").time()
    maximum = request.form.get("max_orders", type=int) or 1
    if start >= end or maximum < 1:
        flash("Enter a valid slot.", "danger")
    else:
        db.session.add(PickupSlot(stall_id=stall.id, start_time=start, end_time=end, max_orders=maximum))
        db.session.commit()
        flash("Pickup slot added.", "success")
    return redirect(url_for("owner.home"))
