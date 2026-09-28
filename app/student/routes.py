"""Browse, cart, checkout, history, favorites, and reviews."""

from decimal import Decimal

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import (
    Complaint,
    Favorite,
    FoodCategory,
    FoodCourt,
    FoodItem,
    Order,
    OrderStatus,
    PickupSlot,
    PlaceStatus,
    Review,
    Role,
    Stall,
)
from app.orders.services import OrderError, cancel_order, place_order
from app.queue.services import recommend_slot
from app.student.services import CartError, add_to_cart, cart_problems, clear_cart, get_cart, update_line
from app.utils.decorators import roles_required

student_bp = Blueprint("student", __name__)


@student_bp.route("/browse")
def browse():
    query = FoodItem.query.join(Stall).join(FoodCourt).join(FoodCategory)
    query = query.filter(Stall.status == PlaceStatus.OPEN, FoodCourt.status == PlaceStatus.OPEN)
    text = (request.args.get("q") or "").strip()
    if text:
        query = query.filter(FoodItem.name.ilike(f"%{text}%"))
    if request.args.get("category"):
        query = query.filter(FoodItem.category_id == request.args.get("category", type=int))
    if request.args.get("stall"):
        query = query.filter(FoodItem.stall_id == request.args.get("stall", type=int))
    if request.args.get("court"):
        query = query.filter(Stall.food_court_id == request.args.get("court", type=int))
    diet = request.args.get("diet")
    if diet == "veg":
        query = query.filter(FoodItem.is_vegetarian.is_(True))
    elif diet == "nonveg":
        query = query.filter(FoodItem.is_vegetarian.is_(False))
    if request.args.get("available") == "1":
        query = query.filter(FoodItem.is_available.is_(True), FoodItem.stock_quantity > 0)
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    if min_price is not None:
        query = query.filter(FoodItem.price >= min_price)
    if max_price is not None:
        query = query.filter(FoodItem.price <= max_price)
    sort = request.args.get("sort") or "name"
    if sort == "price_asc":
        query = query.order_by(FoodItem.price.asc())
    elif sort == "price_desc":
        query = query.order_by(FoodItem.price.desc())
    elif sort == "rating":
        query = query.order_by(FoodItem.rating.desc())
    else:
        query = query.order_by(FoodItem.name.asc())
    page = query.paginate(page=request.args.get("page", 1, type=int), per_page=12, error_out=False)
    return render_template(
        "student/browse.html",
        page=page,
        categories=FoodCategory.query.order_by(FoodCategory.name).all(),
        stalls=Stall.query.filter_by(status=PlaceStatus.OPEN).order_by(Stall.name).all(),
        courts=FoodCourt.query.filter_by(status=PlaceStatus.OPEN).order_by(FoodCourt.name).all(),
    )


@student_bp.route("/food/<int:food_id>")
def food_detail(food_id: int):
    item = db.session.get(FoodItem, food_id)
    if item is None:
        return render_template("errors/404.html"), 404
    return render_template("student/food.html", item=item)


@student_bp.route("/cart")
@login_required
def cart():
    cart_row = get_cart(current_user)
    total = sum((line.food.price * line.quantity for line in cart_row.items), Decimal("0"))
    return render_template("student/cart.html", cart=cart_row, total=total, problems=cart_problems(cart_row))


@student_bp.route("/api/cart/add", methods=["POST"])
@login_required
def cart_add():
    try:
        add_to_cart(current_user, request.form.get("food_id", type=int), request.form.get("quantity", 1, type=int))
    except CartError as exc:
        flash(str(exc), "danger")
    else:
        flash("Added to cart.", "success")
    return redirect(request.referrer or url_for("student.cart"))


@student_bp.route("/api/cart/update", methods=["POST"])
@login_required
def cart_update():
    try:
        update_line(current_user, request.form.get("food_id", type=int), request.form.get("quantity", type=int))
    except CartError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("student.cart"))


@student_bp.route("/api/cart/clear", methods=["POST"])
@login_required
def cart_clear():
    clear_cart(current_user)
    flash("Cart cleared.", "success")
    return redirect(url_for("student.cart"))


@student_bp.route("/checkout", methods=["GET", "POST"])
@login_required
@roles_required(Role.STUDENT)
def checkout():
    cart_row = get_cart(current_user)
    problems = cart_problems(cart_row)
    slots = []
    recommendation = None
    if cart_row.stall_id:
        slots = PickupSlot.query.filter_by(stall_id=cart_row.stall_id).order_by(PickupSlot.start_time).all()
        recommendation = recommend_slot(cart_row.stall, slots)
    if request.method == "POST":
        if problems:
            flash("Fix the cart before checkout.", "danger")
        else:
            try:
                order = place_order(current_user, request.form.get("slot_id", type=int), request.form.get("method"))
            except OrderError as exc:
                flash(str(exc), "danger")
            else:
                if order.payment_method == "ONLINE":
                    return redirect(url_for("payments.mock_page", order_id=order.id))
                return redirect(url_for("orders.detail", order_id=order.id))
    subtotal = sum((line.food.price * line.quantity for line in cart_row.items), Decimal("0"))
    return render_template(
        "student/checkout.html",
        cart=cart_row,
        subtotal=subtotal,
        problems=problems,
        slots=slots,
        recommendation=recommendation,
    )


@student_bp.route("/history")
@login_required
def history():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("student/history.html", orders=orders)


@student_bp.route("/orders/<order_id>/reorder", methods=["POST"])
@login_required
def reorder(order_id: str):
    order = _own_order(order_id)
    clear_cart(current_user)
    for item in order.items:
        try:
            add_to_cart(current_user, item.food_id, item.quantity)
        except CartError as exc:
            flash(str(exc), "danger")
            break
    else:
        flash("Previous items were added to the cart.", "success")
    return redirect(url_for("student.cart"))


@student_bp.route("/orders/<order_id>/cancel", methods=["POST"])
@login_required
def cancel(order_id: str):
    order = _own_order(order_id)
    try:
        cancel_order(order, current_user.id)
    except OrderError as exc:
        flash(str(exc), "danger")
    else:
        flash("Order cancelled.", "success")
    return redirect(url_for("orders.detail", order_id=order.id))


@student_bp.route("/orders/<order_id>/review", methods=["POST"])
@login_required
def review(order_id: str):
    order = _own_order(order_id)
    if order.status != OrderStatus.COLLECTED:
        flash("You can review only a collected order.", "danger")
        return redirect(url_for("orders.detail", order_id=order.id))
    if order.review is not None:
        flash("This order already has a review.", "danger")
        return redirect(url_for("orders.detail", order_id=order.id))
    rating = request.form.get("rating", type=int)
    if rating is None or rating < 1 or rating > 5:
        flash("Choose a rating from 1 to 5.", "danger")
        return redirect(url_for("orders.detail", order_id=order.id))
    db.session.add(
        Review(
            order_id=order.id,
            user_id=current_user.id,
            stall_id=order.stall_id,
            food_id=order.items[0].food_id if order.items else None,
            rating=rating,
            text=(request.form.get("text") or "").strip(),
        )
    )
    db.session.commit()
    flash("Review saved.", "success")
    return redirect(url_for("orders.detail", order_id=order.id))


@student_bp.route("/favorites", methods=["GET", "POST"])
@login_required
def favorites():
    if request.method == "POST":
        target_type = request.form.get("target_type")
        target_id = request.form.get("target_id", type=int)
        existing = Favorite.query.filter_by(
            user_id=current_user.id, target_type=target_type, target_id=target_id
        ).first()
        if existing:
            db.session.delete(existing)
        elif target_type in ("food", "stall") and target_id:
            db.session.add(Favorite(user_id=current_user.id, target_type=target_type, target_id=target_id))
        db.session.commit()
        return redirect(request.referrer or url_for("student.favorites"))
    rows = Favorite.query.filter_by(user_id=current_user.id).all()
    return render_template("student/favorites.html", favorites=rows)


@student_bp.route("/complaints", methods=["POST"])
@login_required
def complaint():
    stall_id = request.form.get("stall_id", type=int)
    message = (request.form.get("message") or "").strip()
    if stall_id and message:
        db.session.add(Complaint(user_id=current_user.id, stall_id=stall_id, message=message))
        db.session.commit()
        flash("Complaint sent to the stall.", "success")
    return redirect(request.referrer or url_for("student.history"))


@student_bp.route("/stats")
@login_required
def stats():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    spent = sum((order.total for order in orders if order.status != OrderStatus.CANCELLED), Decimal("0"))
    return render_template("student/stats.html", orders=orders, spent=spent, count=len(orders))


def _own_order(order_id: str) -> Order:
    order = db.session.get(Order, order_id)
    if order is None or order.user_id != current_user.id:
        abort(403)
    return order
