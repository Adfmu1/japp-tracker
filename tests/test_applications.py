import uuid

import pytest

from app import create_app
from app.models import JobApplication, User, db


class TestConfig:
    SECRET_KEY = "test-secret-key-that-is-at-least-32-characters"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
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
        db.drop_all()


def create_application(client, *, owner_id=None):
    with client.application.app_context():
        owner = db.session.get(User, owner_id) if owner_id else None
        if owner is None:
            owner = User(
                id=uuid.uuid4(),
                username=f"user-{uuid.uuid4()}",
                email=f"{uuid.uuid4()}@example.com",
                password_hash="unused",
            )
            db.session.add(owner)
            db.session.flush()
        application = JobApplication(
            id=uuid.uuid4(),
            user_id=owner.id,
            name="Developer",
            company="Example",
            description="Build things",
            stage="0. Draft",
        )
        db.session.add(application)
        db.session.commit()
        return owner.id, application.id


def login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def test_applications_include_edit_link(client):
    user_id, application_id = create_application(client)
    login(client, user_id)

    response = client.get("/applications")

    assert response.status_code == 200
    assert f"/applications/{application_id}/edit" in response.text


def test_edit_updates_owned_application(client):
    user_id, application_id = create_application(client)
    login(client, user_id)

    response = client.post(
        f"/applications/{application_id}/edit",
        data={
            "name": "Senior Developer",
            "company": "New Example",
            "description": "Lead a team",
            "salary_min": "100000",
            "salary_max": "130000",
            "stage": "1. Applied",
        },
    )

    assert response.status_code == 302
    with client.application.app_context():
        application = db.session.get(JobApplication, application_id)
        assert application.name == "Senior Developer"
        assert application.stage == "1. Applied"


def test_edit_form_is_prefilled_for_owned_application(client):
    user_id, application_id = create_application(client)
    login(client, user_id)

    response = client.get(f"/applications/{application_id}/edit")

    assert response.status_code == 200
    assert 'value="Developer"' in response.text
    assert "Save changes" in response.text


def test_edit_rejects_application_owned_by_another_user(client):
    owner_id, application_id = create_application(client)
    other_user_id, _ = create_application(client)
    login(client, other_user_id)

    response = client.post(
        f"/applications/{application_id}/edit",
        data={
            "name": "Tampered",
            "company": "Example",
            "stage": "0. Draft",
        },
    )

    assert response.status_code == 404
    with client.application.app_context():
        application = db.session.get(JobApplication, application_id)
        assert application.user_id == owner_id
        assert application.name == "Developer"


def test_delete_removes_owned_application(client):
    user_id, application_id = create_application(client)
    login(client, user_id)

    response = client.post(f"/applications/{application_id}/delete")

    assert response.status_code == 302
    with client.application.app_context():
        assert db.session.get(JobApplication, application_id) is None


def test_delete_rejects_application_owned_by_another_user(client):
    owner_id, application_id = create_application(client)
    other_user_id, _ = create_application(client)
    login(client, other_user_id)

    response = client.post(f"/applications/{application_id}/delete")

    assert response.status_code == 404
    with client.application.app_context():
        application = db.session.get(JobApplication, application_id)
        assert application.user_id == owner_id
