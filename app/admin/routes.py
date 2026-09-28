from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.admin.forms import CategoryForm, FoodCourtForm, OwnerForm, StallForm
from app.admin.services import (
    PlaceError,
    create_category,
    create_food_court,
    create_owner,
    create_stall,
    delete_category,
    set_place_status,
    set_suspended,
    update_category,
    update_food_court,
    update_stall,
)
from app.extensions import db
from app.models import FoodCategory, FoodCourt, FoodItem, PlaceStatus, Role, Stall, User
from app.utils.decorators import roles_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _court_or_404(court_id: int) -> FoodCourt:
    court = db.session.get(FoodCourt, court_id)
    if court is None:
        abort(404)
    return court


def _stall_or_404(stall_id: int) -> Stall:
    stall = db.session.get(Stall, stall_id)
    if stall is None:
        abort(404)
    return stall


def _owner_choices():
    owners = User.query.filter_by(role=Role.OWNER).order_by(User.name.asc()).all()
    return [(0, "No court owner")] + [(user.id, f"{user.name} ({user.email})") for user in owners]


def _court_choices():
    return [(court.id, court.name) for court in FoodCourt.query.order_by(FoodCourt.name.asc()).all()]


def _free_stall_choices():
    stalls = Stall.query.filter(Stall.owner_id.is_(None)).order_by(Stall.name.asc()).all()
    return [(stall.id, f"{stall.name} — {stall.food_court.name}") for stall in stalls]


@admin_bp.route("/users")
@roles_required(Role.ADMIN)
def users():
    accounts = User.query.order_by(User.id.asc()).all()
    return render_template("admin/users.html", accounts=accounts)


@admin_bp.route("/users/<int:user_id>/suspend", methods=["POST"])
@roles_required(Role.ADMIN)
def suspend_user(user_id: int):
    return _set_user_suspended(user_id, True)


@admin_bp.route("/users/<int:user_id>/activate", methods=["POST"])
@roles_required(Role.ADMIN)
def activate_user(user_id: int):
    return _set_user_suspended(user_id, False)


def _set_user_suspended(user_id: int, suspended: bool):
    account = db.session.get(User, user_id)
    if account is None:
        abort(404)
    try:
        set_suspended(current_user, account, suspended)
    except PlaceError as exc:
        flash(str(exc), "danger")
    else:
        flash("Account suspended." if suspended else "Account activated.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/courts")
@roles_required(Role.ADMIN)
def courts():
    rows = FoodCourt.query.order_by(FoodCourt.name.asc()).all()
    return render_template("admin/courts.html", courts=rows, statuses=PlaceStatus)


@admin_bp.route("/courts/new", methods=["GET", "POST"])
@roles_required(Role.ADMIN)
def new_court():
    form = FoodCourtForm()
    form.owner_id.choices = _owner_choices()
    if form.validate_on_submit():
        try:
            create_food_court(
                form.name.data,
                form.description.data,
                form.location.data,
                form.opening_time.data,
                form.closing_time.data,
                form.owner_id.data,
                form.image.data,
            )
        except PlaceError as exc:
            flash(str(exc), "danger")
        else:
            flash("Food court created. It stays closed until you approve it.", "success")
            return redirect(url_for("admin.courts"))
    return render_template("admin/court_form.html", form=form, heading="New food court")


@admin_bp.route("/courts/<int:court_id>/edit", methods=["GET", "POST"])
@roles_required(Role.ADMIN)
def edit_court(court_id: int):
    court = _court_or_404(court_id)
    form = FoodCourtForm(obj=court) if request.method == "GET" else FoodCourtForm()
    form.owner_id.choices = _owner_choices()
    if request.method == "GET":
        form.owner_id.data = court.owner_id or 0
    if form.validate_on_submit():
        try:
            update_food_court(
                court,
                form.name.data,
                form.description.data,
                form.location.data,
                form.opening_time.data,
                form.closing_time.data,
                form.owner_id.data,
                form.image.data,
            )
        except PlaceError as exc:
            flash(str(exc), "danger")
        else:
            flash("Food court updated.", "success")
            return redirect(url_for("admin.courts"))
    return render_template("admin/court_form.html", form=form, heading="Edit food court")


@admin_bp.route("/courts/<int:court_id>/status", methods=["POST"])
@roles_required(Role.ADMIN)
def court_status(court_id: int):
    court = _court_or_404(court_id)
    _apply_status(court)
    return redirect(url_for("admin.courts"))


@admin_bp.route("/stalls")
@roles_required(Role.ADMIN)
def stalls():
    rows = Stall.query.order_by(Stall.name.asc()).all()
    return render_template("admin/stalls.html", stalls=rows, statuses=PlaceStatus)


@admin_bp.route("/stalls/new", methods=["GET", "POST"])
@roles_required(Role.ADMIN)
def new_stall():
    form = StallForm()
    form.food_court_id.choices = _court_choices()
    if not form.food_court_id.choices:
        flash("Create a food court before adding a stall.", "warning")
        return redirect(url_for("admin.courts"))
    if form.validate_on_submit():
        try:
            create_stall(
                form.food_court_id.data,
                form.name.data,
                form.description.data,
                form.location.data,
                form.contact.data,
                form.opening_time.data,
                form.closing_time.data,
                form.image.data,
            )
        except PlaceError as exc:
            flash(str(exc), "danger")
        else:
            flash("Stall created. It stays closed until you approve it.", "success")
            return redirect(url_for("admin.stalls"))
    return render_template("admin/stall_form.html", form=form, heading="New stall")


@admin_bp.route("/stalls/<int:stall_id>/edit", methods=["GET", "POST"])
@roles_required(Role.ADMIN)
def edit_stall(stall_id: int):
    stall = _stall_or_404(stall_id)
    form = StallForm(obj=stall) if request.method == "GET" else StallForm()
    form.food_court_id.choices = _court_choices()
    if request.method == "GET":
        form.food_court_id.data = stall.food_court_id
    if form.validate_on_submit():
        try:
            update_stall(
                stall,
                form.food_court_id.data,
                form.name.data,
                form.description.data,
                form.location.data,
                form.contact.data,
                form.opening_time.data,
                form.closing_time.data,
                form.image.data,
            )
        except PlaceError as exc:
            flash(str(exc), "danger")
        else:
            flash("Stall updated.", "success")
            return redirect(url_for("admin.stalls"))
    return render_template("admin/stall_form.html", form=form, heading="Edit stall")


@admin_bp.route("/stalls/<int:stall_id>/status", methods=["POST"])
@roles_required(Role.ADMIN)
def stall_status(stall_id: int):
    stall = _stall_or_404(stall_id)
    _apply_status(stall)
    return redirect(url_for("admin.stalls"))


@admin_bp.route("/owners/new", methods=["GET", "POST"])
@roles_required(Role.ADMIN)
def new_owner():
    form = OwnerForm()
    form.stall_id.choices = _free_stall_choices()
    if not form.stall_id.choices:
        flash("Every stall already has an owner, or there is no stall yet.", "warning")
        return redirect(url_for("admin.stalls"))
    if form.validate_on_submit():
        try:
            owner = create_owner(form.name.data, form.email.data, form.password.data, form.stall_id.data)
        except PlaceError as exc:
            flash(str(exc), "danger")
        else:
            flash(f"Owner {owner.email} can now log in and manage that stall only.", "success")
            return redirect(url_for("admin.stalls"))
    return render_template("admin/owner_form.html", form=form)


def _apply_status(place) -> None:
    status = request.form.get("status", "")
    try:
        set_place_status(place, status)
    except PlaceError as exc:
        flash(str(exc), "danger")
    else:
        label = {PlaceStatus.OPEN: "Approved and open.", PlaceStatus.CLOSED: "Marked closed.", PlaceStatus.TEMPORARILY_CLOSED: "Marked temporarily closed."}
        flash(label[status], "success")


@admin_bp.route("/categories", methods=["GET", "POST"])
@roles_required(Role.ADMIN)
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        try:
            create_category(form.name.data, form.description.data)
        except PlaceError as exc:
            flash(str(exc), "danger")
        else:
            flash("Category saved.", "success")
            return redirect(url_for("admin.categories"))
    rows = FoodCategory.query.order_by(FoodCategory.name.asc()).all()
    return render_template("admin/categories.html", categories=rows, form=form)


@admin_bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@roles_required(Role.ADMIN)
def edit_category(category_id: int):
    category = db.session.get(FoodCategory, category_id)
    if category is None:
        abort(404)
    form = CategoryForm(obj=category) if request.method == "GET" else CategoryForm()
    if form.validate_on_submit():
        try:
            update_category(category, form.name.data, form.description.data)
        except PlaceError as exc:
            flash(str(exc), "danger")
        else:
            flash("Category updated.", "success")
            return redirect(url_for("admin.categories"))
    return render_template("admin/category_form.html", form=form, category=category)


@admin_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@roles_required(Role.ADMIN)
def remove_category(category_id: int):
    category = db.session.get(FoodCategory, category_id)
    if category is None:
        abort(404)
    try:
        delete_category(category)
    except PlaceError as exc:
        flash(str(exc), "danger")
    else:
        flash("Category removed.", "success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/food")
@roles_required(Role.ADMIN)
def food():
    items = FoodItem.query.order_by(FoodItem.name.asc()).all()
    return render_template("admin/food.html", items=items)
