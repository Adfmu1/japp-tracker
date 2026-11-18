from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp


class RegistrationForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=40),
            Regexp(r"^\w+$", message="Only letters, numbers and underscores"),
        ],
    )
    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=80)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8)],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match"),
        ],
    )
    submit = SubmitField("Register")
