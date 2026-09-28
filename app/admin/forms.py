from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import PasswordField, SelectField, StringField, SubmitField, TextAreaField, TimeField
from wtforms.validators import DataRequired, Length


class FoodCourtForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[Length(max=500)])
    location = StringField("Location", validators=[DataRequired(), Length(max=160)])
    opening_time = TimeField("Opening time", format="%H:%M", validators=[DataRequired()])
    closing_time = TimeField("Closing time", format="%H:%M", validators=[DataRequired()])
    image = FileField(
        "Logo",
        validators=[FileAllowed(["png", "jpg", "jpeg", "webp"], "Use a png, jpg, or webp image.")],
    )
    owner_id = SelectField("Court owner", coerce=int, default=0)
    submit = SubmitField("Save food court")


class StallForm(FlaskForm):
    food_court_id = SelectField("Food court", coerce=int, validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[Length(max=500)])
    location = StringField("Location", validators=[DataRequired(), Length(max=160)])
    contact = StringField("Contact", validators=[DataRequired(), Length(max=80)])
    opening_time = TimeField("Opening time", format="%H:%M", validators=[DataRequired()])
    closing_time = TimeField("Closing time", format="%H:%M", validators=[DataRequired()])
    image = FileField(
        "Logo",
        validators=[FileAllowed(["png", "jpg", "jpeg", "webp"], "Use a png, jpg, or webp image.")],
    )
    submit = SubmitField("Save stall")


class OwnerForm(FlaskForm):
    name = StringField("Owner name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    stall_id = SelectField("Stall", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Create owner")


class CategoryForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=80)])
    description = StringField("Description", validators=[Length(max=255)])
    submit = SubmitField("Save category")
