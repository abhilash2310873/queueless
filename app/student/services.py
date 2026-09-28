"""Student cart rules. One cart holds food from one stall only."""

from app.extensions import db
from app.models import Cart, CartItem, FoodItem


class CartError(Exception):
    pass


def get_cart(user) -> Cart:
    if user.cart is None:
        user.cart = Cart(user_id=user.id)
        db.session.add(user.cart)
        db.session.commit()
    return user.cart


def add_to_cart(user, food_id: int, quantity: int) -> Cart:
    if quantity < 1:
        raise CartError("Quantity must be at least 1.")
    food = db.session.get(FoodItem, food_id)
    if food is None:
        raise CartError("That food item does not exist.")
    if not food.is_available or food.stock_quantity < quantity:
        raise CartError("That item is sold out." if food.stock_quantity <= 0 or not food.is_available else f"Only {food.stock_quantity} item remaining." if food.stock_quantity == 1 else f"Only {food.stock_quantity} items remaining.")
    cart = get_cart(user)
    if cart.stall_id is not None and cart.stall_id != food.stall_id and cart.items:
        raise CartError("Your cart contains items from another stall. Clear cart or checkout separately.")
    cart.stall_id = food.stall_id
    existing = next((line for line in cart.items if line.food_id == food.id), None)
    new_qty = quantity if existing is None else existing.quantity + quantity
    if new_qty > food.stock_quantity:
        raise CartError(f"Only {food.stock_quantity} items remaining.")
    if existing is None:
        db.session.add(CartItem(cart_id=cart.id, food_id=food.id, quantity=quantity))
    else:
        existing.quantity = new_qty
    db.session.commit()
    return cart


def update_line(user, food_id: int, quantity: int) -> None:
    cart = get_cart(user)
    line = next((item for item in cart.items if item.food_id == food_id), None)
    if line is None:
        raise CartError("That item is not in your cart.")
    if quantity < 1:
        db.session.delete(line)
    else:
        if quantity > line.food.stock_quantity or not line.food.is_available:
            raise CartError("That quantity is no longer available.")
        line.quantity = quantity
    db.session.flush()
    if not cart.items:
        cart.stall_id = None
    db.session.commit()


def clear_cart(user) -> None:
    cart = get_cart(user)
    cart.items.clear()
    cart.stall_id = None
    db.session.commit()


def cart_problems(cart: Cart) -> list[str]:
    problems = []
    for line in cart.items:
        food = line.food
        if not food.is_available or food.stock_quantity <= 0:
            problems.append(f"{food.name} is sold out.")
        elif line.quantity > food.stock_quantity:
            problems.append(f"Only {food.stock_quantity} {food.name} remaining.")
    return problems
