"""Signed pickup tokens. The QR image contains only this token, not a name or payment."""

import io
import secrets

import qrcode
from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.models import Order, OrderStatus, PaymentStatus


def sign_order(order: Order) -> str:
    if not order.qr_nonce:
        order.qr_nonce = secrets.token_urlsafe(16)
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="pickup")
    return serializer.dumps({"order_id": order.id, "nonce": order.qr_nonce})


def qr_png(token: str) -> bytes:
    image = qrcode.make(token)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def read_token(token: str) -> Order:
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="pickup")
    try:
        # max_age is one day. A copied token from last week will not scan.
        payload = serializer.loads(token, max_age=60 * 60 * 24)
    except SignatureExpired as exc:
        raise QRError("This pickup token has expired.") from exc
    except BadSignature as exc:
        raise QRError("This pickup token is not valid.") from exc
    order = db_get(payload.get("order_id"))
    if order is None or order.qr_nonce != payload.get("nonce"):
        raise QRError("This pickup token is not valid.")
    return order


def db_get(order_id):
    from app.extensions import db

    return db.session.get(Order, order_id)


class QRError(Exception):
    pass


def assert_collectable(order: Order, stall_id: int) -> None:
    if order.stall_id != stall_id:
        raise QRError("This ticket is for another stall.")
    if order.status == OrderStatus.COLLECTED:
        raise QRError("Order already collected.")
    if order.status != OrderStatus.READY:
        raise QRError("This order is not ready for collection.")
    payment = order.payment
    if payment is None or payment.status not in (PaymentStatus.SUCCESS, PaymentStatus.CASH_PAID):
        raise QRError("Payment is still pending.")
