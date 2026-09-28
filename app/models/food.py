"""Food courts, stalls, categories, and menu items."""

from decimal import Decimal

from app.extensions import db
from app.models.user import utcnow


class PlaceStatus:
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    TEMPORARILY_CLOSED = "TEMPORARILY_CLOSED"
    CHOICES = (OPEN, CLOSED, TEMPORARILY_CLOSED)


class FoodCourt(db.Model):
    __tablename__ = "food_courts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    location = db.Column(db.String(160), nullable=False)
    opening_time = db.Column(db.Time, nullable=False)
    closing_time = db.Column(db.Time, nullable=False)
    image_path = db.Column(db.String(255))
    # New courts stay CLOSED until an admin approves them (sets OPEN).
    status = db.Column(db.String(32), nullable=False, default=PlaceStatus.CLOSED, index=True)
    # Who is responsible for the court. Stall access uses stalls.owner_id, not this column.
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    owner = db.relationship("User", foreign_keys=[owner_id], backref="managed_courts")
    stalls = db.relationship("Stall", back_populates="food_court", order_by="Stall.name")


class Stall(db.Model):
    __tablename__ = "stalls"
    __table_args__ = (db.UniqueConstraint("food_court_id", "name", name="uq_stall_name_per_court"),)

    id = db.Column(db.Integer, primary_key=True)
    food_court_id = db.Column(db.Integer, db.ForeignKey("food_courts.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    location = db.Column(db.String(160), nullable=False)
    contact = db.Column(db.String(80), nullable=False)
    # One staff login per stall. This is the check that blocks another owner.
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=True)
    opening_time = db.Column(db.Time, nullable=False)
    closing_time = db.Column(db.Time, nullable=False)
    image_path = db.Column(db.String(255))
    status = db.Column(db.String(32), nullable=False, default=PlaceStatus.CLOSED, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    food_court = db.relationship("FoodCourt", back_populates="stalls")
    owner = db.relationship("User", foreign_keys=[owner_id], backref=db.backref("owned_stall", uselist=False))
    food_items = db.relationship("FoodItem", back_populates="stall", order_by="FoodItem.name")


class FoodCategory(db.Model):
    """Shared labels such as Breakfast or Beverages. Admins create these; they are not hard-coded."""

    __tablename__ = "food_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    food_items = db.relationship("FoodItem", back_populates="category")


class FoodItem(db.Model):
    __tablename__ = "food_items"
    __table_args__ = (db.UniqueConstraint("stall_id", "name", name="uq_food_name_per_stall"),)

    id = db.Column(db.Integer, primary_key=True)
    stall_id = db.Column(db.Integer, db.ForeignKey("stalls.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("food_categories.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    price = db.Column(db.Numeric(8, 2), nullable=False)
    image_path = db.Column(db.String(255))
    # Minutes a cook typically needs. Queue wait times will use this later.
    prep_time_minutes = db.Column(db.Integer, nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    # Manual flag. An owner can hide an item even when stock remains.
    is_available = db.Column(db.Boolean, nullable=False, default=True, index=True)
    is_vegetarian = db.Column(db.Boolean, nullable=False, default=True)
    rating = db.Column(db.Numeric(3, 2), nullable=False, default=Decimal("0.00"))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    stall = db.relationship("Stall", back_populates="food_items")
    category = db.relationship("FoodCategory", back_populates="food_items")

    @property
    def availability_label(self) -> str:
        if self.stock_quantity <= 0:
            return "SOLD OUT"
        if not self.is_available:
            return "CURRENTLY UNAVAILABLE"
        return "AVAILABLE"
