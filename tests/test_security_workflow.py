from pathlib import Path

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "security-gates.yml"


def test_security_workflow_has_all_blocking_gates():
    workflow = WORKFLOW.read_text()

    for job in ("dependency-scan", "secret-scan", "filesystem-scan"):
        assert f"{job}:" in workflow

    assert "pip-audit" in workflow
    assert "gitleaks" in workflow
    assert (
        "trivy@sha256:029e990b328d149bf0a9ffe355919041e1f86192db2df47e217f8a36dd42ceac"
        in workflow
    )
    assert "config /repo/infra/aws" in workflow
    assert "MEDIUM,HIGH,CRITICAL" in workflow
    assert "--exit-code 1" in workflow


def test_secret_scan_redacts_findings_and_workflow_does_not_apply_terraform():
    workflow = WORKFLOW.read_text()

    assert "--redact" in workflow
    assert "terraform apply" not in workflow
