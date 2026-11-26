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

    assert "release_commit:" in workflow
    assert "RELEASE_COMMIT" in workflow
    assert "JAPP_RELEASE_COMMIT" in workflow
    assert "migration_result" in workflow
    assert "rollout_result" in workflow
    assert "GITHUB_STEP_SUMMARY" in workflow


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
