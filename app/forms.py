from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
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


class LoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(max=40)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired()],
    )
    remember = BooleanField("Remember me")
    submit = SubmitField("Log in")


class ChangeUsernameForm(FlaskForm):
    username = StringField(
        "New username",
        validators=[
            DataRequired(),
            Length(min=3, max=40),
            Regexp(r"^\w+$", message="Only letters, numbers and underscores"),
        ],
    )
    password = PasswordField(
        "Current password",
        validators=[DataRequired()],
    )
    submit = SubmitField("Save")


class ChangeEmailForm(FlaskForm):
    email = StringField(
        "New email",
        validators=[DataRequired(), Email(), Length(max=80)],
    )
    password = PasswordField(
        "Current password",
        validators=[DataRequired()],
    )
    submit = SubmitField("Save")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Current password",
        validators=[DataRequired()],
    )
    password = PasswordField(
        "New password",
        validators=[DataRequired(), Length(min=8)],
    )
    confirm_password = PasswordField(
        "Confirm new password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match"),
        ],
    )
    submit = SubmitField("Save")
