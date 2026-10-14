"""Payment providers. The order code asks this factory which one to use."""

from flask import current_app


class PaymentError(Exception):
    pass


class PaymentProvider:
    name = "base"

    def start(self, order) -> str:
        raise NotImplementedError


class MockPaymentProvider(PaymentProvider):
    """Local stand-in. The student clicks success or failure. No card data."""

    name = "mock"

    def start(self, order) -> str:
        return f"/pay/{order.id}"


class RazorpayPaymentProvider(PaymentProvider):
    """Placeholder for a real gateway. It refuses to run without keys."""

    name = "razorpay"

    def start(self, order) -> str:
        key = current_app.config.get("RAZORPAY_KEY_ID") or ""
        secret = current_app.config.get("RAZORPAY_KEY_SECRET") or ""
        if not key or not secret:
            raise PaymentError("Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET before using Razorpay.")
        return f"razorpay:{order.id}"


def get_provider() -> PaymentProvider:
    name = (current_app.config.get("PAYMENT_PROVIDER") or "mock").lower()
    if name == "razorpay":
        return RazorpayPaymentProvider()
    return MockPaymentProvider()
