from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, ValidationError



class RegisterForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Length(max=255)])
    student_id = StringField("Roll number", validators=[DataRequired(), Length(max=40)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords do not match.")],
    )
    submit = SubmitField("Create account")

    def validate_email(self, field):
        email = (field.data or "").strip()
        if email.count("@") != 1 or "." not in email.split("@", 1)[1]:
            raise ValidationError("Enter a valid email address.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")


class VerifyCodeForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Length(max=255)])
    code = StringField("Verification code", validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField("Verify")


class ResendForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Length(max=255)])
    submit = SubmitField("Send a new code")
