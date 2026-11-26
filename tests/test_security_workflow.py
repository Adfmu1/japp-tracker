from pathlib import Path

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "security-gates.yml"


def test_security_workflow_has_all_blocking_gates():
    workflow = WORKFLOW.read_text()

    for job in ("dependency-scan", "secret-scan", "filesystem-scan", "container-scan"):
        assert f"{job}:" in workflow

    assert "pip-audit" in workflow
    assert "gitleaks" in workflow
    assert "trivy:0.59.1" in workflow
    assert "config /repo/infra/aws" in workflow
    assert "image japp-security:${GITHUB_SHA}" in workflow
    assert "--pkg-types os" in workflow
    assert "MEDIUM,HIGH,CRITICAL" in workflow
    assert "--exit-code 1" in workflow


def test_secret_scan_redacts_findings_and_workflow_does_not_apply_terraform():
    workflow = WORKFLOW.read_text()

    assert "--redact" in workflow
    assert "terraform apply" not in workflow
