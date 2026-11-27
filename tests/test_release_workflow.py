import re
from pathlib import Path

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "release.yml"


def read_workflow() -> str:
    return WORKFLOW.read_text()


def test_release_waits_for_successful_ci_and_security_workflows_on_main():
    workflow = read_workflow()

    assert "workflow_run:" in workflow
    assert "- CI" in workflow
    assert "- Security gates" in workflow
    assert "branches: [main]" in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow
    assert "workflow_run.name == 'CI'" in workflow
    assert "workflow_run.head_branch == 'main'" in workflow


def test_release_gate_lookup_explicitly_targets_github_repository_before_checkout():
    workflow = read_workflow()
    gate_wait_step = workflow.split("      - name: Wait for both required gates", 1)[1]
    gate_wait_step = gate_wait_step.split(
        "      - name: Check out the gated commit", 1
    )[0]
    gh_run_list = gate_wait_step.split("gh run list", 1)[1].split(")", 1)[0]

    assert '--repo "$GITHUB_REPOSITORY"' in gh_run_list


def test_release_builds_and_pushes_one_sha_tagged_ecr_image():
    workflow = read_workflow()

    assert "docker/build-push-action@" in workflow
    assert "push: true" in workflow
    assert "tags: |" in workflow
    assert ":sha-${{ github.event.workflow_run.head_sha }}" in workflow
    assert "github.event.workflow_run.head_sha" in workflow
    assert "aws-actions/configure-aws-credentials@" in workflow
    assert "aws-actions/amazon-ecr-login@" in workflow
    assert "environment:" not in workflow


def test_release_records_digest_and_hands_off_only_digest_identity():
    workflow = read_workflow()

    assert "digest: ${{ steps.build.outputs.digest }}" in workflow
    assert "image-digest.txt" in workflow
    assert "Scan the exact release image" in workflow
    assert 'image "$IMAGE"' in workflow
    assert "--pkg-types os" in workflow
    assert "sha256:" in workflow
    assert (
        "needs.release.outputs.digest" in workflow
        or "steps.build.outputs.digest" in workflow
    )
    assert "docker tag" not in workflow
    assert ":latest" not in workflow


def test_release_uses_keyless_cosign_and_attaches_provenance():
    workflow = read_workflow()

    assert "id-token: write" in workflow
    assert "cosign sign --yes" in workflow
    assert "cosign.pub" not in workflow
    assert "actions/attest-build-provenance@" in workflow
    assert "push-to-registry: true" in workflow
    assert "attestations: write" in workflow


def test_release_publishes_machine_readable_artifact_metadata_for_cd():
    workflow = read_workflow()

    assert "actions/upload-artifact@" in workflow
    assert "release-metadata" in workflow
    assert "image=${IMAGE}" in workflow
    assert "digest=${DIGEST}" in workflow
    assert "commit=${RELEASE_SHA}" in workflow
    assert "verify the signature" in workflow.lower()


def test_deploy_workflow_requires_commit_identity_and_records_release_results():
    workflow = (WORKFLOW.parent / "deploy.yml").read_text()

    assert "release_commit=$commit" in workflow
    assert "RELEASE_COMMIT" in workflow
    assert "JAPP_RELEASE_COMMIT" in workflow
    assert "migration_result" in workflow
    assert "rollout_result" in workflow
    assert "GITHUB_STEP_SUMMARY" in workflow


def test_deploy_workflow_accepts_only_a_verified_release_run_metadata_artifact():
    workflow = (WORKFLOW.parent / "deploy.yml").read_text()

    assert "release_run_id:" in workflow
    assert "gh api" in workflow
    assert '.event == "workflow_run"' in workflow
    assert '.head_branch == "main"' in workflow
    assert "gh run download" in workflow
    assert "repository=" in (WORKFLOW.parent / "release.yml").read_text()
    assert "describe-images" in workflow
    assert "imageTag=sha-${RELEASE_COMMIT}" in workflow
    assert "cosign verify" in workflow
    assert "inputs.image_ref" not in workflow
    assert "inputs.release_commit" not in workflow
    assert "inputs.signer" not in workflow


def test_deploy_installs_cosign_and_logs_into_ecr_before_verification():
    release = read_workflow()
    deploy = (WORKFLOW.parent / "deploy.yml").read_text()
    first_verify = re.search(
        r"^[ \t]*(?:run:[ \t]+)?cosign verify\b", deploy, re.MULTILINE
    )
    assert first_verify, "deploy.yml must verify the release signature"
    before_verify = deploy[: first_verify.start()]

    for action, description in (
        ("sigstore/cosign-installer", "Cosign installer"),
        ("aws-actions/amazon-ecr-login", "ECR login"),
    ):
        action_ref = rf"^[ \t]*uses: {re.escape(action)}@"
        end_of_ref = r"[ \t]*(?:#|$)"
        release_pin = re.search(
            rf"{action_ref}([0-9a-f]{{40}}){end_of_ref}", release, re.MULTILINE
        )
        assert release_pin, f"release.yml must pin the {description} to a commit SHA"
        deploy_step = re.search(
            rf"{action_ref}{release_pin[1]}{end_of_ref}", before_verify, re.MULTILINE
        )
        assert deploy_step, (
            f"deploy.yml must run the {description} with the release.yml pin "
            "before the first cosign verify"
        )
        if action == "aws-actions/amazon-ecr-login":
            assert re.search(
                r"^[ \t]*uses: aws-actions/configure-aws-credentials@",
                before_verify[: deploy_step.start()],
                re.MULTILINE,
            ), "deploy.yml must configure AWS credentials before ECR login"


def test_production_deploy_is_main_only_and_requires_explicit_approval():
    workflow = (WORKFLOW.parent / "deploy.yml").read_text()

    assert "workflow_dispatch:" in workflow
    assert "environment: production" in workflow
    assert "if: github.ref == 'refs/heads/main'" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "Only the main branch" in workflow


def test_release_candidate_and_deploy_evidence_include_signer_and_rollback():
    release = read_workflow()
    deploy = (WORKFLOW.parent / "deploy.yml").read_text()

    assert "production candidate" in release.lower()
    assert "signer=${COSIGN_CERTIFICATE_IDENTITY}" in release
    assert "candidate-evidence" in release
    assert "superseded" in release.lower()
    assert "signer_result" in deploy
    assert "rollback_result" in deploy
    assert "approved_by" in deploy
    assert "deployment_status=failed" in deploy


def test_production_trust_policy_excludes_feature_branches():
    policy = (WORKFLOW.parents[2] / "infra" / "aws" / "iam.tf").read_text()

    assert '"repo:${var.github_repository}:ref:refs/heads/main"' in policy
    assert '"repo:${var.github_repository}:environment:production"' in policy
    assert "refs/heads/*" not in policy
    assert "pull_request" not in policy
