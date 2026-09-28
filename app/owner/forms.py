from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import SelectField, StringField, SubmitField, TextAreaField, TimeField
from wtforms.validators import DataRequired, Length

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
