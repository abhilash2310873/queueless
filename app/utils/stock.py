"""Stock changes that must stay correct when two orders arrive together.

The deduction is one UPDATE with a condition in the WHERE clause. The database
applies that statement on its own, so two requests cannot both pass a Python
"if stock >= qty" check and then both write.
"""

from sqlalchemy import case, update

from app.extensions import db
from app.models import FoodItem


class StockError(Exception):
    """Not enough stock, or a quantity that does not make sense."""


def deduct_stock(food_id: int, quantity: int) -> int:
    """Subtract quantity in one conditional UPDATE. Returns the stock left.

    If no row changes, another order already took the units, or the item is
    unavailable. The caller should show the error and not create the order.
    """
    if quantity < 1:
        raise StockError("Quantity must be at least 1.")

    sold_out_after = FoodItem.stock_quantity - quantity <= 0
    statement = (
        update(FoodItem)
        .where(
            FoodItem.id == food_id,
            FoodItem.is_available.is_(True),
            FoodItem.stock_quantity >= quantity,
        )
        .values(
            stock_quantity=FoodItem.stock_quantity - quantity,
            # Same statement: a row that hits zero is no longer orderable.
            is_available=case((sold_out_after, False), else_=FoodItem.is_available),
        )
        .execution_options(synchronize_session=False)
    )
    result = db.session.execute(statement)
    if result.rowcount != 1:
        db.session.rollback()
        raise StockError(_shortage_message(food_id))

    db.session.commit()
    item = db.session.get(FoodItem, food_id)
    db.session.refresh(item)
    return item.stock_quantity


def restore_stock(food_id: int, quantity: int) -> int:
    """Add quantity back with one UPDATE. Used later when an order is cancelled.

    Restocking does not mark the item available again. The owner does that.
    """
    if quantity < 1:
        raise StockError("Quantity must be at least 1.")
    statement = (
        update(FoodItem)
        .where(FoodItem.id == food_id)
        .values(stock_quantity=FoodItem.stock_quantity + quantity)
        .execution_options(synchronize_session=False)
    )
    result = db.session.execute(statement)
    if result.rowcount != 1:
        db.session.rollback()
        raise StockError("That food item does not exist.")
    db.session.commit()
    item = db.session.get(FoodItem, food_id)
    db.session.refresh(item)
    return item.stock_quantity


def _shortage_message(food_id: int) -> str:
    item = db.session.get(FoodItem, food_id)
    if item is None:
        return "That food item does not exist."
    remaining = item.stock_quantity
    if remaining <= 0 or not item.is_available:
        return "That item is sold out."
    if remaining == 1:
        return "Only 1 item remaining."
    return f"Only {remaining} items remaining."
