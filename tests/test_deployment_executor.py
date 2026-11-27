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


def test_workflow_passes_public_acceptance_contract_to_executor():
    text = WORKFLOW.read_text()

    assert "JAPP_PUBLIC_URL" in text
    assert "JAPP_EXPECTED_HOSTNAME" in text
    assert "acceptance_result" in text
    assert "JAPP_PUBLIC_URL=" in text
    assert "JAPP_EXPECTED_HOSTNAME=" in text


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
            "JAPP_RELEASE_COMMIT": "a" * 40,
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 10
    assert "deployment_status=authentication_failure" in result.stdout


def test_executor_serializes_releases_and_records_release_identity():
    text = EXECUTOR.read_text()

    assert "flock" in text
    assert "JAPP_DEPLOYMENT_LOCK_FILE" in text
    assert "JAPP_RELEASE_COMMIT" in text
    assert "release_commit=" in text
    assert "release_digest=" in text


def test_executor_migration_failure_precedes_any_application_change():
    text = EXECUTOR.read_text()

    migration = text.index("migration_succeeded")
    application_apply = text.index('apply -f "$rendered_app"')
    assert migration < application_apply
    assert "migration_failed" in text
    assert "rollout_succeeded" in text
    assert "delete job japp-db-migrate --ignore-not-found=true" in text


def test_executor_requires_complete_production_acceptance_contract():
    text = EXECUTOR.read_text()

    assert "rollout_succeeded" in text
    assert "healthz_succeeded" in text
    assert "readyz_succeeded" in text
    assert "gateway_succeeded" in text
    assert "certificate_succeeded" in text
    assert "https_redirect_succeeded" in text
    assert "JAPP_EXPECTED_HOSTNAME" in text
    assert 'kubectl -n "$NAMESPACE" get gateway' in text
    assert 'kubectl -n "$NAMESPACE" get httproute' in text
    assert "curl --fail" in text
    assert "--location" in text
    assert "--max-redirs" in text


def test_executor_rolls_back_every_acceptance_failure_without_migration_rollback():
    text = EXECUTOR.read_text()

    acceptance_start = text.index("rollback_application()")
    acceptance = text[acceptance_start:]

    assert 'set image deployment/"' in acceptance
    assert "previous_image" in acceptance
    assert 'kubectl -n "$NAMESPACE" delete job' not in acceptance
    assert "migration_succeeded" in text
    assert 'fail "$CLUSTER_FAILURE" "acceptance_failed_rolled_back"' in text


def test_executor_does_not_disable_tls_verification_or_print_diagnostics():
    text = EXECUTOR.read_text()

    assert "--insecure" not in text
    assert " -k" not in text
    assert "curl --verbose" not in text
    assert "kubectl describe" not in text


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
            "JAPP_RELEASE_COMMIT": "a" * 40,
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 20
    assert "deployment_status=secret_sync_failure" in result.stdout
    assert "do-not-print-this-secret" not in result.stdout
    assert "do-not-print-this-secret" not in result.stderr


def _write_mock_command(path: Path, body: str) -> None:
    path.write_text(f"#!/bin/sh\nset -eu\n{body}\n")
    path.chmod(0o700)


def _executor_env(bin_dir: Path, log_file: Path, manifest_dir: Path) -> dict[str, str]:
    return {
        **os.environ,
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "MOCK_LOG": str(log_file),
        "JAPP_MANIFEST_DIR": str(manifest_dir),
        "JAPP_DEPLOYMENT_LOCK_FILE": str(manifest_dir / "deploy.lock"),
        "COSIGN_CERTIFICATE_IDENTITY": "release@example.invalid",
        "COSIGN_OIDC_ISSUER": "https://token.actions.githubusercontent.com",
        "JAPP_RELEASE_COMMIT": "a" * 40,
        "JAPP_PUBLIC_URL": "https://jobs.example.invalid",
        "JAPP_EXPECTED_HOSTNAME": "jobs.example.invalid",
    }


def _prepare_executor_mocks(
    tmp_path: Path, kubectl_body: str
) -> tuple[Path, Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_file = tmp_path / "commands.log"
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    (manifest_dir / "migration-job.yaml").write_text("image: __IMAGE__\n")
    (manifest_dir / "app.yaml").write_text("image: __IMAGE__\n")
    _write_mock_command(bin_dir / "cosign", "exit 0")
    _write_mock_command(
        bin_dir / "aws",
        'if [ "$1" = secretsmanager ]; then printf \'{"KEY":"secret-value"}\'; else exit 1; fi',
    )
    _write_mock_command(
        bin_dir / "kubectl",
        'printf "%s\\n" "$*" >> "$MOCK_LOG"\n'
        'case "$*" in *"apply -f -"*) cat >/dev/null ;; esac\n' + kubectl_body,
    )
    return bin_dir, log_file, manifest_dir


def test_executor_mock_contract_stops_before_rollout_when_migration_fails(tmp_path):
    bin_dir, log_file, manifest_dir = _prepare_executor_mocks(
        tmp_path,
        """
        case "$*" in
          *"get deployment"*) printf 'registry.example/app@sha256:%064d\\n' 0 ;;
          *"wait"*"job/japp-db-migrate"*) exit 1 ;;
          *"create secret"*) printf 'apiVersion: v1\\n' ;;
          *) exit 0 ;;
        esac
        """,
    )
    result = subprocess.run(
        [str(EXECUTOR), "registry.example/app@sha256:" + "b" * 64, "app", "db"],
        env=_executor_env(bin_dir, log_file, manifest_dir),
        capture_output=True,
        text=True,
        check=False,
    )

    log = log_file.read_text()
    assert result.returncode == 40
    assert "migration_failed" in result.stdout
    assert "delete job japp-db-migrate" in log
    assert "apply -f" in log
    assert "app.yaml" not in log
    assert "secret-value" not in result.stdout + result.stderr


def test_executor_mock_contract_rolls_back_application_without_reversing_migration(
    tmp_path,
):
    bin_dir, log_file, manifest_dir = _prepare_executor_mocks(
        tmp_path,
        """
        case "$*" in
          *"get deployment"*) printf 'registry.example/app@sha256:%064d\\n' 0 ;;
          *"wait"*"job/japp-db-migrate"*) exit 0 ;;
          *"rollout status"*)
            count="$(grep -c 'rollout status' "$MOCK_LOG" || true)"
            [ "$count" -gt 1 ] && exit 0 || exit 1
            ;;
          *"create secret"*) printf 'apiVersion: v1\\n' ;;
          *) exit 0 ;;
        esac
        """,
    )
    result = subprocess.run(
        [str(EXECUTOR), "registry.example/app@sha256:" + "b" * 64, "app", "db"],
        env=_executor_env(bin_dir, log_file, manifest_dir),
        capture_output=True,
        text=True,
        check=False,
    )

    log = log_file.read_text()
    assert result.returncode == 40
    assert "rollout_failed" in result.stdout
    assert "set image deployment/japp-app app=registry.example/app@sha256=" not in log
    assert "set image deployment/japp-app app=registry.example/app@sha256:" in log
    assert log.count("delete job japp-db-migrate") == 1
    assert "secret-value" not in result.stdout + result.stderr


def test_executor_mock_contract_rolls_back_after_acceptance_failure(tmp_path):
    bin_dir, log_file, manifest_dir = _prepare_executor_mocks(
        tmp_path,
        """
        case "$*" in
          *"get deployment"*) printf 'registry.example/app@sha256:%064d\\n' 0 ;;
          *"create secret"*) printf 'apiVersion: v1\\n' ;;
          *) exit 0 ;;
        esac
        """,
    )
    _write_mock_command(
        bin_dir / "curl",
        'case "$*" in *"/healthz"*) exit 1 ;; *) exit 0 ;; esac',
    )
    result = subprocess.run(
        [str(EXECUTOR), "registry.example/app@sha256:" + "b" * 64, "app", "db"],
        env=_executor_env(bin_dir, log_file, manifest_dir),
        capture_output=True,
        text=True,
        check=False,
    )

    log = log_file.read_text()
    assert result.returncode == 40
    assert "acceptance_failed_rolled_back" in result.stdout
    assert "set image deployment/japp-app app=registry.example/app@sha256:" in log
    assert log.count("delete job japp-db-migrate") == 1
    assert "secret-value" not in result.stdout + result.stderr
