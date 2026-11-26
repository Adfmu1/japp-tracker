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
    assert "${{ github.sha }}" in workflow
    assert "aws-actions/configure-aws-credentials@" in workflow
    assert "aws-actions/amazon-ecr-login@" in workflow
    assert "environment:" not in workflow


def test_release_records_digest_and_hands_off_only_digest_identity():
    workflow = read_workflow()

    assert "outputs: digest" in workflow
    assert "digest: ${{ steps.build.outputs.digest }}" in workflow
    assert "image-digest.txt" in workflow
    assert "sha256:" in workflow
    assert "needs.release.outputs.digest" in workflow or "steps.build.outputs.digest" in workflow
    assert "docker tag" not in workflow
    assert "latest" not in workflow


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
    assert "commit=${GITHUB_SHA}" in workflow
    assert "verify the signature" in workflow.lower()
