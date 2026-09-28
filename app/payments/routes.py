"""Mock online payment. No card number is collected or stored."""

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Order
from app.orders.services import OrderError, confirm_online_payment

payments_bp = Blueprint("payments", __name__, url_prefix="/payment")


@payments_bp.route("/<order_id>")
@login_required
def mock_page(order_id: str):
    order = _own(order_id)
    return render_template("payments/mock.html", order=order)


@payments_bp.route("/<order_id>/success", methods=["POST"])
@login_required
def mock_success(order_id: str):
    return _finish(order_id, True)


@payments_bp.route("/<order_id>/failure", methods=["POST"])
@login_required
def mock_failure(order_id: str):
    return _finish(order_id, False)


def _finish(order_id: str, success: bool):
    order = _own(order_id)
    try:
        confirm_online_payment(order, success)
    except OrderError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("orders.detail", order_id=order.id))


def _own(order_id: str) -> Order:
    order = db.session.get(Order, order_id)
    if order is None or order.user_id != current_user.id:
        abort(403)
    return order
