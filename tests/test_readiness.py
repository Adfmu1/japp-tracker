import os
from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from app.models import db


class TestConfig:
    SECRET_KEY = "test-secret-key-that-is-at-least-32-characters"
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
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


def test_readyz_returns_200_when_database_query_succeeds(client):
    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.text == "ready"


def test_readyz_returns_503_when_database_query_fails(client):
    with patch.object(db.session, "execute", side_effect=SQLAlchemyError):
        response = client.get("/readyz")

    assert response.status_code == 503
    assert response.text == "database unavailable"
