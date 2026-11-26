from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    IntegerField,
    PasswordField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    Optional,
    Regexp,
    ValidationError,
)


class RegistrationForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=40),
            Regexp(
                r"^[A-Za-z0-9_]+\Z",
                message="Only letters, numbers and underscores",
            ),
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
            Regexp(
                r"^[A-Za-z0-9_]+\Z",
                message="Only letters, numbers and underscores",
            ),
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


class DeleteAccountForm(FlaskForm):
    password = PasswordField(
        "Current password",
        validators=[DataRequired()],
    )
    submit = SubmitField("Delete account")


class JobApplicationForm(FlaskForm):
    name = StringField(
        "Position",
        validators=[DataRequired(), Length(max=120)],
    )
    company = StringField(
        "Company",
        validators=[DataRequired(), Length(max=120)],
    )
    description = TextAreaField(
        "Description",
        validators=[Optional()],
    )
    salary_min = IntegerField(
        "Minimum salary",
        validators=[Optional(), NumberRange(min=0)],
    )
    salary_max = IntegerField(
        "Maximum salary",
        validators=[Optional(), NumberRange(min=0)],
    )
    stage = StringField(
        "Stage",
        validators=[DataRequired(), Length(max=120)],
        default="0. Draft",
    )
    submit = SubmitField("Add application")

    def validate_salary_max(self, field: IntegerField) -> None:
        if (
            self.salary_min.data is not None
            and field.data is not None
            and field.data < self.salary_min.data
        ):
            raise ValidationError(
                "Maximum salary must be greater than or equal to the minimum salary."
            )


class DeleteApplicationForm(FlaskForm):
    pass
