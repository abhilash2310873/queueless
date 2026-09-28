"""Order page, status polling, and the QR image."""

from flask import Blueprint, abort, jsonify, render_template, send_file
import io

from flask_login import current_user, login_required

from app.extensions import db
from app.models import Order, Role
from app.orders.qr import qr_png, sign_order
from app.orders.services import delay_flag
from app.queue.services import queue_snapshot

orders_bp = Blueprint("orders", __name__, url_prefix="/orders")


def _visible(order: Order) -> Order:
    if order is None:
        abort(404)
    if current_user.role == Role.ADMIN:
        return order
    if current_user.role == Role.OWNER and current_user.owned_stall and order.stall_id == current_user.owned_stall.id:
        return order
    if order.user_id != current_user.id:
        abort(403)
    return order


@orders_bp.route("/<order_id>")
@login_required
def detail(order_id: str):
    order = _visible(db.session.get(Order, order_id))
    snapshot = queue_snapshot(order) if order.queue_number else None
    token = sign_order(order) if order.qr_nonce or order.queue_number else None
    if token and not order.qr_nonce:
        db.session.commit()
    return render_template(
        "orders/detail.html",
        order=order,
        snapshot=snapshot,
        delay=delay_flag(order),
        token=token,
    )


@orders_bp.route("/<order_id>/status")
@login_required
def status(order_id: str):
    order = _visible(db.session.get(Order, order_id))
    snapshot = queue_snapshot(order) if order.queue_number else None
    return jsonify(
        {
            "status": order.status,
            "queue_number": order.queue_number,
            "payment_status": order.payment.status if order.payment else None,
            "snapshot": snapshot,
            "delay": delay_flag(order),
        }
    )


@orders_bp.route("/<order_id>/qr")
@login_required
def qr(order_id: str):
    order = _visible(db.session.get(Order, order_id))
    if not order.queue_number:
        abort(404)
    token = sign_order(order)
    db.session.commit()
    return send_file(io.BytesIO(qr_png(token)), mimetype="image/png")
