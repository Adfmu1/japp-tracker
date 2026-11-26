from pathlib import Path

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml"


def test_ci_workflow_validates_pull_requests_and_main_pushes():
    workflow = WORKFLOW.read_text()

    assert "pull_request:" in workflow
    assert "push:" in workflow
    assert "branches: [main]" in workflow
    assert "ruff check ." in workflow
    assert "ruff format --check ." in workflow
    assert "pytest" in workflow


def test_ci_workflow_provides_postgresql_without_exposing_credentials():
    workflow = WORKFLOW.read_text()

    assert "postgres:16" in workflow
    assert "POSTGRES_PASSWORD: postgres" in workflow
    assert "TEST_DATABASE_URL: postgresql+psycopg2://postgres:postgres@" in workflow
    assert "DB_URL: postgresql+psycopg2://postgres:postgres@" in workflow
    assert "SECRET_KEY:" in workflow
    assert "secrets." not in workflow
