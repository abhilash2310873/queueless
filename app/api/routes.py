"""JSON API used by the React app. The HTML pages call the same services."""

from decimal import Decimal

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from app.auth.services import (
    AuthError,
    clear_login_failures,
    login_is_locked,
    record_login_failure,
    register_student,
    request_password_reset,
    reset_password,
    verify_with_code,
)
from app.extensions import db
from app.models import (
    ActivityLog,
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
    User,
)
from app.orders.qr import sign_order
from app.orders.services import OrderError, cancel_order, change_status, collect_with_token, mark_cash_paid, place_order
from app.queue.services import queue_snapshot, recommend_slot
from app.student.services import CartError, add_to_cart, cart_problems, clear_cart, get_cart, update_line
from app.utils.decorators import roles_required

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def _user(user):
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "student_id": user.student_id,
        "stall_id": user.owned_stall.id if user.role == Role.OWNER and user.owned_stall else None,
    }


def _food(item: FoodItem):
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "price": float(item.price),
        "prep_time_minutes": item.prep_time_minutes,
        "stock_quantity": item.stock_quantity,
        "is_available": item.is_available,
        "is_vegetarian": item.is_vegetarian,
        "availability": item.availability_label,
        "rating": float(item.rating or 0),
        "category": item.category.name,
        "category_id": item.category_id,
        "stall": item.stall.name,
        "stall_id": item.stall_id,
        "court": item.stall.food_court.name,
    }


def _order(order: Order):
    snapshot = queue_snapshot(order) if order.queue_number else None
    token = None
    if order.queue_number:
        token = sign_order(order)
        db.session.commit()
    return {
        "id": order.id,
        "queue_number": order.queue_number,
        "status": order.status,
        "total": float(order.total),
        "method": order.payment_method,
        "payment_status": order.payment.status if order.payment else None,
        "stall": order.stall.name,
        "court": order.food_court.name,
        "created_at": order.created_at.isoformat(),
        "items": [
            {"name": item.name, "quantity": item.quantity, "price": float(item.unit_price), "food_id": item.food_id}
            for item in order.items
        ],
        "snapshot": snapshot,
        "token": token,
        "has_review": order.review is not None,
    }


@api_bp.get("/me")
def me():
    return jsonify({"user": _user(current_user)})


@api_bp.post("/auth/register")
def register():
    data = request.get_json(force=True, silent=True) or {}
    try:
        register_student(data.get("name", ""), data.get("email", ""), data.get("password", ""), data.get("student_id", ""))
    except AuthError as exc:
        return jsonify({"error": str(exc)}), 400
    from flask import g

    payload = {"ok": True, "message": "Account created. Enter the verification code."}
    code = getattr(g, "dev_verification_code", None)
    if code:
        payload["dev_code"] = code
        payload["message"] = f"Account created. Your verification code is {code}."
    return jsonify(payload)


@api_bp.post("/auth/verify")
def verify():
    data = request.get_json(force=True, silent=True) or {}
    try:
        verify_with_code(data.get("email", ""), data.get("code", ""))
    except AuthError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True})


@api_bp.post("/auth/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if login_is_locked(email):
        return jsonify({"error": "Too many login attempts. Wait 10 minutes and try again."}), 429
    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(data.get("password") or ""):
        record_login_failure(email)
        return jsonify({"error": "Email or password is incorrect."}), 400
    if user.is_suspended:
        return jsonify({"error": "This account is suspended."}), 403
    if not user.email_verified:
        return jsonify({"error": "Verify your email before signing in."}), 400
    login_user(user)
    clear_login_failures(email)
    db.session.add(ActivityLog(actor_id=user.id, action="login", detail=user.email))
    db.session.commit()
    return jsonify({"user": _user(user)})


@api_bp.post("/auth/forgot")
def forgot():
    data = request.get_json(force=True, silent=True) or {}
    request_password_reset(data.get("email", ""))
    from flask import g

    payload = {"ok": True, "message": "If that account exists, use the reset token."}
    token = getattr(g, "dev_reset_token", None)
    if token:
        payload["dev_token"] = token
        payload["message"] = f"Reset token: {token}"
    return jsonify(payload)


@api_bp.post("/auth/reset")
def reset():
    data = request.get_json(force=True, silent=True) or {}
    try:
        reset_password(data.get("token", ""), data.get("password", ""))
    except AuthError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True})


@api_bp.post("/auth/logout")
@login_required
def logout():
    db.session.add(ActivityLog(actor_id=current_user.id, action="logout", detail=current_user.email))
    db.session.commit()
    logout_user()
    return jsonify({"ok": True})


@api_bp.get("/browse")
def browse():
    query = FoodItem.query.join(Stall).join(FoodCourt)
    query = query.filter(Stall.status == PlaceStatus.OPEN, FoodCourt.status == PlaceStatus.OPEN)
    text = (request.args.get("q") or "").strip()
    if text:
        query = query.filter(FoodItem.name.ilike(f"%{text}%"))
    if request.args.get("category"):
        query = query.filter(FoodItem.category_id == request.args.get("category", type=int))
    if request.args.get("diet") == "veg":
        query = query.filter(FoodItem.is_vegetarian.is_(True))
    elif request.args.get("diet") == "nonveg":
        query = query.filter(FoodItem.is_vegetarian.is_(False))
    if request.args.get("available") == "1":
        query = query.filter(FoodItem.is_available.is_(True), FoodItem.stock_quantity > 0)
    sort = request.args.get("sort") or "name"
    if sort == "price_asc":
        query = query.order_by(FoodItem.price.asc())
    elif sort == "price_desc":
        query = query.order_by(FoodItem.price.desc())
    elif sort == "rating":
        query = query.order_by(FoodItem.rating.desc())
    else:
        query = query.order_by(FoodItem.name.asc())
    items = query.limit(60).all()
    return jsonify(
        {
            "items": [_food(item) for item in items],
            "categories": [{"id": row.id, "name": row.name} for row in FoodCategory.query.order_by(FoodCategory.name).all()],
        }
    )


@api_bp.get("/food/<int:food_id>")
def food(food_id: int):
    item = db.session.get(FoodItem, food_id)
    if item is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(_food(item))


@api_bp.get("/cart")
@login_required
def cart():
    row = get_cart(current_user)
    total = sum((line.food.price * line.quantity for line in row.items), Decimal("0"))
    slots = []
    recommendation = None
    if row.stall_id:
        slots = PickupSlot.query.filter_by(stall_id=row.stall_id).order_by(PickupSlot.start_time).all()
        recommendation = recommend_slot(row.stall, slots)
    return jsonify(
        {
            "stall": row.stall.name if row.stall else None,
            "court": row.stall.food_court.name if row.stall else None,
            "items": [
                {
                    "food_id": line.food_id,
                    "name": line.food.name,
                    "quantity": line.quantity,
                    "price": float(line.food.price),
                    "availability": line.food.availability_label,
                }
                for line in row.items
            ],
            "total": float(total),
            "problems": cart_problems(row),
            "slots": [
                {"id": slot.id, "label": slot.label, "spaces_left": slot.spaces_left, "full": slot.spaces_left == 0}
                for slot in slots
            ],
            "recommendation": None
            if recommendation is None
            else {"slot_id": recommendation["slot"].id, "label": recommendation["slot"].label, "reason": recommendation["reason"]},
        }
    )


@api_bp.post("/cart/add")
@login_required
def cart_add():
    data = request.get_json(force=True, silent=True) or {}
    try:
        add_to_cart(current_user, int(data.get("food_id") or 0), int(data.get("quantity") or 1))
    except (CartError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True})


@api_bp.post("/cart/update")
@login_required
def cart_update():
    data = request.get_json(force=True, silent=True) or {}
    try:
        update_line(current_user, int(data.get("food_id") or 0), int(data.get("quantity") or 0))
    except (CartError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True})


@api_bp.post("/cart/clear")
@login_required
def cart_clear():
    clear_cart(current_user)
    return jsonify({"ok": True})


@api_bp.post("/checkout")
@roles_required(Role.STUDENT)
def checkout():
    data = request.get_json(force=True, silent=True) or {}
    try:
        order = place_order(current_user, int(data.get("slot_id") or 0), data.get("method") or "CASH")
    except (OrderError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(_order(order))


@api_bp.post("/payment/<order_id>/<result>")
@login_required
def payment(order_id: str, result: str):
    from app.orders.services import confirm_online_payment

    order = db.session.get(Order, order_id)
    if order is None or order.user_id != current_user.id:
        return jsonify({"error": "Not allowed"}), 403
    try:
        confirm_online_payment(order, result == "success")
    except OrderError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(_order(order))


@api_bp.get("/orders")
@login_required
def orders():
    rows = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return jsonify({"orders": [_order(row) for row in rows]})


@api_bp.get("/orders/<order_id>")
@login_required
def order_detail(order_id: str):
    order = db.session.get(Order, order_id)
    if order is None:
        return jsonify({"error": "Not found"}), 404
    if current_user.role == Role.ADMIN:
        pass
    elif current_user.role == Role.OWNER and current_user.owned_stall and order.stall_id == current_user.owned_stall.id:
        pass
    elif order.user_id != current_user.id:
        return jsonify({"error": "Not allowed"}), 403
    return jsonify(_order(order))


@api_bp.post("/orders/<order_id>/cancel")
@login_required
def cancel(order_id: str):
    order = db.session.get(Order, order_id)
    try:
        cancel_order(order, current_user.id)
    except OrderError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(_order(order))


@api_bp.post("/orders/<order_id>/review")
@login_required
def review(order_id: str):
    order = db.session.get(Order, order_id)
    if order is None or order.user_id != current_user.id:
        return jsonify({"error": "Not allowed"}), 403
    if order.status != OrderStatus.COLLECTED or order.review is not None:
        return jsonify({"error": "You can review a collected order once."}), 400
    data = request.get_json(force=True, silent=True) or {}
    rating = int(data.get("rating") or 0)
    if rating < 1 or rating > 5:
        return jsonify({"error": "Choose a rating from 1 to 5."}), 400
    db.session.add(
        Review(
            order_id=order.id,
            user_id=current_user.id,
            stall_id=order.stall_id,
            food_id=order.items[0].food_id if order.items else None,
            rating=rating,
            text=(data.get("text") or "").strip(),
        )
    )
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.get("/favorites")
@login_required
def favorites():
    rows = Favorite.query.filter_by(user_id=current_user.id).all()
    return jsonify({"favorites": [{"id": row.id, "target_type": row.target_type, "target_id": row.target_id} for row in rows]})


@api_bp.post("/favorites")
@login_required
def favorite_toggle():
    data = request.get_json(force=True, silent=True) or {}
    target_type = data.get("target_type")
    target_id = int(data.get("target_id") or 0)
    existing = Favorite.query.filter_by(user_id=current_user.id, target_type=target_type, target_id=target_id).first()
    if existing:
        db.session.delete(existing)
    elif target_type in ("food", "stall"):
        db.session.add(Favorite(user_id=current_user.id, target_type=target_type, target_id=target_id))
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.get("/owner/orders")
@roles_required(Role.OWNER)
def owner_orders():
    stall = current_user.owned_stall
    if stall is None:
        return jsonify({"orders": [], "stall": None})
    from app.queue.predictor import demand_level, sellout_insights

    rows = Order.query.filter_by(stall_id=stall.id).order_by(Order.created_at.desc()).limit(30).all()
    insights = sellout_insights(stall.id)
    demand = demand_level(stall.id)
    return jsonify({"stall": stall.name, "orders": [_order(row) for row in rows], "insights": insights, "demand": demand})


@api_bp.post("/owner/orders/<order_id>/<action>")
@roles_required(Role.OWNER)
def owner_action(order_id: str, action: str):
    stall = current_user.owned_stall
    order = db.session.get(Order, order_id)
    if stall is None or order is None or order.stall_id != stall.id:
        return jsonify({"error": "Not allowed"}), 403
    mapping = {
        "accept": OrderStatus.ACCEPTED,
        "preparing": OrderStatus.PREPARING,
        "ready": OrderStatus.READY,
        "reject": OrderStatus.REJECTED,
    }
    data = request.get_json(force=True, silent=True) or {}
    try:
        if action == "cash":
            mark_cash_paid(order, current_user.id)
        elif action == "collect":
            collect_with_token(data.get("token") or "", stall.id, current_user.id)
        elif action in mapping:
            change_status(order, mapping[action], current_user.id)
        else:
            return jsonify({"error": "Unknown action"}), 404
    except OrderError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(_order(order))


@api_bp.get("/owner/menu")
@roles_required(Role.OWNER)
def owner_menu():
    stall = current_user.owned_stall
    if stall is None:
        return jsonify({"items": []})
    return jsonify({"stall": stall.name, "items": [_food(item) for item in stall.food_items]})


@api_bp.get("/admin/summary")
@roles_required(Role.ADMIN)
def admin_summary_route():
    from app.analytics.services import admin_summary

    summary = admin_summary()
    return jsonify(
        {
            "students": summary["students"],
            "owners": summary["owners"],
            "orders": summary["orders"],
            "revenue": float(summary["revenue"] or 0),
            "users": [_user(user) for user in User.query.order_by(User.id).all()],
            "courts": [{"id": court.id, "name": court.name, "status": court.status} for court in FoodCourt.query.all()],
            "stalls": [{"id": stall.id, "name": stall.name, "status": stall.status} for stall in Stall.query.all()],
            "complaints": [{"message": row.message} for row in Complaint.query.limit(20).all()],
            "categories": [{"id": row.id, "name": row.name} for row in FoodCategory.query.order_by(FoodCategory.name).all()],
        }
    )


def _clock(value: str):
    from datetime import datetime

    return datetime.strptime(value, "%H:%M").time()


@api_bp.post("/admin/courts")
@roles_required(Role.ADMIN)
def create_court_api():
    from app.admin.services import PlaceError, create_food_court

    data = request.get_json(force=True, silent=True) or {}
    try:
        court = create_food_court(
            data.get("name", ""),
            data.get("description", ""),
            data.get("location", ""),
            _clock(data.get("opening_time") or "08:00"),
            _clock(data.get("closing_time") or "20:00"),
            0,
        )
    except (PlaceError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"id": court.id, "name": court.name, "status": court.status})


@api_bp.post("/admin/stalls")
@roles_required(Role.ADMIN)
def create_stall_api():
    from app.admin.services import PlaceError, create_stall

    data = request.get_json(force=True, silent=True) or {}
    try:
        stall = create_stall(
            int(data.get("food_court_id") or 0),
            data.get("name", ""),
            data.get("description", ""),
            data.get("location", ""),
            data.get("contact", ""),
            _clock(data.get("opening_time") or "09:00"),
            _clock(data.get("closing_time") or "21:00"),
        )
    except (PlaceError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"id": stall.id, "name": stall.name})


@api_bp.post("/admin/categories")
@roles_required(Role.ADMIN)
def create_category_api():
    from app.admin.services import PlaceError, create_category

    data = request.get_json(force=True, silent=True) or {}
    try:
        category = create_category(data.get("name", ""), data.get("description", ""))
    except PlaceError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"id": category.id, "name": category.name})


@api_bp.post("/owner/food")
@roles_required(Role.OWNER)
def create_owner_food():
    from app.owner.services import FoodError, create_food_item

    stall = current_user.owned_stall
    if stall is None:
        return jsonify({"error": "No stall is assigned."}), 400
    data = request.get_json(force=True, silent=True) or {}
    try:
        item = create_food_item(
            current_user,
            stall,
            int(data.get("category_id") or 0),
            data.get("name", ""),
            data.get("description", ""),
            data.get("price") or 0,
            int(data.get("prep_time_minutes") or 1),
            int(data.get("stock_quantity") or 0),
            True,
            bool(data.get("is_vegetarian", True)),
        )
    except (FoodError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(_food(item))
