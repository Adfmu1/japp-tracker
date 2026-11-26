import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
EXECUTOR = ROOT / "deploy" / "ec2-deployment-executor.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"


def test_executor_exists_and_exposes_safe_status_contract():
    assert EXECUTOR.exists()
    text = EXECUTOR.read_text()

    assert "AUTHENTICATION_FAILURE=10" in text
    assert "SECRET_SYNC_FAILURE=20" in text
    assert "MANIFEST_FAILURE=30" in text
    assert "CLUSTER_FAILURE=40" in text
    assert "cosign verify" in text
    assert "secretsmanager get-secret-value" in text
    assert 'kubectl -n "$NAMESPACE" apply -f -' in text


def test_executor_rejects_mutable_or_malformed_image_references():
    text = EXECUTOR.read_text()

    assert "sha256:" in text
    assert "latest" in text
    assert "IMAGE_REF" in text


def test_executor_never_prints_secret_command_output():
    text = EXECUTOR.read_text()

    assert "set -x" not in text
    assert "SecretString" in text
    assert 'kubectl -n "$NAMESPACE" apply -f - >/dev/null' in text
    assert 'echo "$' not in text


def test_workflow_uses_oidc_ssm_and_protected_environment():
    assert WORKFLOW.exists()
    text = WORKFLOW.read_text()

    assert "id-token: write" in text
    assert "environment: production" in text
    assert "aws-actions/configure-aws-credentials" in text
    assert "aws ssm send-command" in text
    assert "aws ssm get-command-invocation" in text
    assert "AWS_SSM_INSTANCE_ID" in text


def test_workflow_does_not_contain_live_ids_or_secrets():
    text = WORKFLOW.read_text()

    assert "i-" not in text
    assert "AKIA" not in text
    assert "password" not in text.lower()


def test_executor_rejects_a_mutable_tag_before_external_calls():
    result = subprocess.run(
        [str(EXECUTOR), "registry.example/app:latest", "app-secret", "db-secret"],
        env={
            **os.environ,
            "COSIGN_CERTIFICATE_IDENTITY": "release@example.invalid",
            "COSIGN_OIDC_ISSUER": "https://token.actions.githubusercontent.com",
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 10
    assert "deployment_status=authentication_failure" in result.stdout


def test_executor_redacts_secret_manager_failure_with_mocked_commands(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "cosign").write_text("#!/bin/sh\nexit 0\n")
    (bin_dir / "aws").write_text(
        "#!/bin/sh\nprintf 'do-not-print-this-secret' >&2\nexit 1\n"
    )
    for command in ("cosign", "aws"):
        (bin_dir / command).chmod(0o700)

    image_ref = "registry.example/app@sha256:" + "a" * 64
    result = subprocess.run(
        [str(EXECUTOR), image_ref, "app-secret", "db-secret"],
        env={
            **os.environ,
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "COSIGN_CERTIFICATE_IDENTITY": "release@example.invalid",
            "COSIGN_OIDC_ISSUER": "https://token.actions.githubusercontent.com",
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 20
    assert "deployment_status=secret_sync_failure" in result.stdout
    assert "do-not-print-this-secret" not in result.stdout
    assert "do-not-print-this-secret" not in result.stderr
