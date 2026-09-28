from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import BooleanField, DecimalField, IntegerField, SelectField, StringField, SubmitField, TextAreaField, TimeField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange

from app.models import PlaceStatus


class OwnerStallForm(FlaskForm):
    """Fields an owner may change. The food court and the owner id are not on this form."""

    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[Length(max=500)])
    location = StringField("Location", validators=[DataRequired(), Length(max=160)])
    contact = StringField("Contact", validators=[DataRequired(), Length(max=80)])
    opening_time = TimeField("Opening time", format="%H:%M", validators=[DataRequired()])
    closing_time = TimeField("Closing time", format="%H:%M", validators=[DataRequired()])
    status = SelectField("Status", choices=[(value, value.replace("_", " ").title()) for value in PlaceStatus.CHOICES])
    image = FileField(
        "Logo",
        validators=[FileAllowed(["png", "jpg", "jpeg", "webp"], "Use a png, jpg, or webp image.")],
    )
    submit = SubmitField("Save stall")


class FoodItemForm(FlaskForm):
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[Length(max=500)])
    price = DecimalField("Price (₹)", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    prep_time_minutes = IntegerField("Preparation time (minutes)", validators=[DataRequired(), NumberRange(min=1, max=240)])
    stock_quantity = IntegerField("Stock quantity", validators=[InputRequired(), NumberRange(min=0)])
    is_vegetarian = BooleanField("Vegetarian")
    is_available = BooleanField("Available to order", default=True)
    image = FileField(
        "Photo",
        validators=[FileAllowed(["png", "jpg", "jpeg", "webp"], "Use a png, jpg, or webp image.")],
    )
    submit = SubmitField("Save food")
