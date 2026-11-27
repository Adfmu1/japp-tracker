import os
import uuid

import pytest

from app import create_app
from app.models import JobApplication, User, db


class TestConfig:
    SECRET_KEY = "test-secret-key-that-is-at-least-32-characters"
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    RATELIMIT_STORAGE_URI = "memory://"


@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def create_user(client):
    with client.application.app_context():
        user = User(
            id=uuid.uuid4(),
            username=f"user-{uuid.uuid4().hex[:8]}",
            email=f"{uuid.uuid4()}@example.com",
        )
        user.set_password("correct-password")
        db.session.add(user)
        db.session.commit()
        return user.id


def login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def add_application(client, user_id):
    with client.application.app_context():
        application = JobApplication(
            id=uuid.uuid4(),
            user_id=user_id,
            name="Developer",
            company="Example",
            description="Build things",
            stage="0. Draft",
        )
        db.session.add(application)
        db.session.commit()


def test_account_page_shows_delete_form(client):
    user_id = create_user(client)
    login(client, user_id)

    response = client.get("/account")

    assert response.status_code == 200
    assert 'name="password"' in response.text
    assert "Delete account" in response.text


def test_delete_account_rejects_incorrect_password(client):
    user_id = create_user(client)
    login(client, user_id)

    response = client.post(
        "/account/delete",
        data={"password": "wrong-password"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Incorrect password." in response.text
    with client.application.app_context():
        assert db.session.get(User, user_id) is not None


def test_delete_account_removes_user_and_applications(client):
    user_id = create_user(client)
    add_application(client, user_id)
    login(client, user_id)

    response = client.post(
        "/account/delete",
        data={"password": "correct-password"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Account deleted." in response.text
    with client.application.app_context():
        assert db.session.get(User, user_id) is None
        assert (
            db.session.execute(
                db.select(JobApplication).filter_by(user_id=user_id)
            ).scalar_one_or_none()
            is None
        )


def test_delete_account_logs_user_out(client):
    user_id = create_user(client)
    login(client, user_id)

    client.post(
        "/account/delete",
        data={"password": "correct-password"},
    )

    response = client.get("/account")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_delete_account_requires_authentication(client):
    response = client.post(
        "/account/delete",
        data={"password": "correct-password"},
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
