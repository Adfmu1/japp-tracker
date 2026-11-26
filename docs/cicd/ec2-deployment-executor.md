# EC2 deployment executor

The production deployment workflow invokes
`/opt/japp/bin/ec2-deployment-executor.sh` on the managed EC2 instance through
AWS Systems Manager. The host image/bootstrap process is responsible for
installing this script, `aws`, `cosign`, `jq`, `kubectl`, and the checked-out
k0s manifests under `/opt/japp/k8s`; application CD does not copy files from a
developer workstation.

## Contract

```text
ec2-deployment-executor.sh IMAGE_REF APP_SECRET_ID DB_SECRET_ID
```

`IMAGE_REF` must be a fully-qualified registry reference ending in a 64-digit
`sha256` digest. The executor verifies that exact reference with keyless Cosign
using `COSIGN_CERTIFICATE_IDENTITY` and `COSIGN_OIDC_ISSUER` before reading
Secrets Manager or changing Kubernetes state.

`JAPP_RELEASE_COMMIT` contains the 40-character source commit SHA. The executor
acquires `JAPP_DEPLOYMENT_LOCK_FILE` (default:
`/var/lock/japp-production-deployment.lock`) before verification and holds it
through migration, rollout, and smoke checks. This serializes releases and
migrations on the single-node host.

Secrets are captured in mode-0600 temporary files and converted directly to
Kubernetes Secret manifests through `kubectl ... --dry-run=client -o yaml |
kubectl apply -f -`. Secret values are never arguments, status output, or
workflow output. Temporary files are removed on exit.

The executor applies the migration Job and waits for completion before applying
the application Deployment. A migration failure emits `migration_failed` and
exits before applying the Deployment. It records the previous digest, requires
rollout success (including the Deployment readiness probe), then verifies the
public HTTPS contract: `/healthz`, database-backed `/readyz`, Gateway `Accepted`
and `Programmed`, both HTTPRoutes `Accepted` and `ResolvedRefs`, the expected
hostname, normal certificate validation, and an HTTP redirect to HTTPS.

`JAPP_PUBLIC_URL` must be an `https://` URL and
`JAPP_EXPECTED_HOSTNAME` must exactly match its hostname. Curl runs without
certificate-warning bypasses and follows only bounded HTTPS redirects. A failed
rollout or acceptance check restores the previous application digest. Database
migrations are not automatically reversed; a successful migration remains in
place during application rollback. Status output includes the release commit and
digest, plus migration, rollout, and acceptance results. Diagnostics are
status-only and never include command output or secret values.

Migration revisions must follow expand/contract compatibility: add or widen
schema elements before the application depends on them, keep the previous
release able to run during the rollout, and remove obsolete elements only in a
later release.

## SSM result codes

| Exit code | Meaning |
| ---: | --- |
| 0 | Deployment succeeded |
| 10 | Image reference or signature authentication failed |
| 20 | Secrets Manager retrieval or Kubernetes Secret synchronization failed |
| 30 | Required manifests could not be read or rendered |
| 40 | Migration, rollout, acceptance, or rollback cluster operation failed |
| 64 | Invalid executor invocation |

The GitHub Actions workflow uses a protected `production` environment,
GitHub OIDC, and repository/environment variables for the target instance,
secret identifiers, and role ARN. No live IDs or secret material belong in this
repository.
