#!/usr/bin/env bash
set -Eeuo pipefail

# Exit codes are part of the SSM contract. Output contains status only; command
# output from AWS, cosign, kubectl, and curl is deliberately discarded.
readonly AUTHENTICATION_FAILURE=10
readonly SECRET_SYNC_FAILURE=20
readonly MANIFEST_FAILURE=30
readonly CLUSTER_FAILURE=40
readonly USAGE_FAILURE=64

readonly NAMESPACE="${JAPP_NAMESPACE:-japp}"
readonly DEPLOYMENT="${JAPP_DEPLOYMENT:-japp-app}"
readonly APP_SECRET_NAME="${JAPP_APP_SECRET_NAME:-app-secrets}"
readonly DB_SECRET_NAME="${JAPP_DB_SECRET_NAME:-db-secrets}"
readonly MANIFEST_DIR="${JAPP_MANIFEST_DIR:-/opt/japp/k8s}"
readonly DEPLOYMENT_LOCK_FILE="${JAPP_DEPLOYMENT_LOCK_FILE:-/var/lock/japp-production-deployment.lock}"
readonly PUBLIC_URL="${JAPP_PUBLIC_URL:-}"
readonly EXPECTED_HOSTNAME="${JAPP_EXPECTED_HOSTNAME:-}"

status() {
  printf 'deployment_status=%s release_commit=%s release_digest=%s\n' \
    "$1" "$RELEASE_COMMIT" "$RELEASE_DIGEST"
}

fail() {
  local code="$1"
  local stage="$2"
  status "$stage"
  exit "$code"
}

usage() {
  printf 'usage: %s IMAGE_REF APP_SECRET_ID DB_SECRET_ID\n' "$0" >&2
  exit "$USAGE_FAILURE"
}

[[ $# -eq 3 ]] || usage
readonly IMAGE_REF="$1"
readonly APP_SECRET_ID="$2"
readonly DB_SECRET_ID="$3"
readonly RELEASE_COMMIT="${JAPP_RELEASE_COMMIT:?JAPP_RELEASE_COMMIT is required}"
readonly RELEASE_DIGEST="${IMAGE_REF##*@}"
readonly COSIGN_IDENTITY="${COSIGN_CERTIFICATE_IDENTITY:?COSIGN_CERTIFICATE_IDENTITY is required}"
readonly COSIGN_ISSUER="${COSIGN_OIDC_ISSUER:?COSIGN_OIDC_ISSUER is required}"

# Hold the lock across verification, migration, rollout, and smoke checks so
# releases cannot race one another on the single-node target.
exec 9>"$DEPLOYMENT_LOCK_FILE"
flock 9

if [[ ! "$RELEASE_COMMIT" =~ ^[a-f0-9]{40}$ ]]; then
  fail "$AUTHENTICATION_FAILURE" "authentication_failure"
fi

# Only a fully-qualified digest is accepted. In particular, tags such as
# "latest" are never passed to Kubernetes.
if [[ ! "$IMAGE_REF" =~ ^[a-z0-9./_-]+@sha256:[a-f0-9]{64}$ ]]; then
  fail "$AUTHENTICATION_FAILURE" "authentication_failure"
fi

if ! cosign verify \
  --certificate-identity "$COSIGN_IDENTITY" \
  --certificate-oidc-issuer "$COSIGN_ISSUER" \
  "$IMAGE_REF" >/dev/null 2>&1; then
  fail "$AUTHENTICATION_FAILURE" "authentication_failure"
fi
status "image_verified"

app_secret_file="$(mktemp)"
db_secret_file="$(mktemp)"
app_env_file="$(mktemp)"
db_env_file="$(mktemp)"
trap 'rm -f "$app_secret_file" "$db_secret_file" "$app_env_file" "$db_env_file"' EXIT
chmod 600 "$app_secret_file" "$db_secret_file" "$app_env_file" "$db_env_file"

# SecretString is captured in a protected temporary file. It is never expanded
# into a log line, shell trace, SSM parameter, or process argument.
if ! aws secretsmanager get-secret-value \
  --secret-id "$APP_SECRET_ID" \
  --query SecretString \
  --output text >"$app_secret_file" 2>/dev/null ||
  ! aws secretsmanager get-secret-value \
  --secret-id "$DB_SECRET_ID" \
  --query SecretString \
  --output text >"$db_secret_file" 2>/dev/null; then
  fail "$SECRET_SYNC_FAILURE" "secret_sync_failure"
fi

if ! jq -e 'type == "object" and all(.[]; type == "string")' "$app_secret_file" >/dev/null ||
  ! jq -e 'type == "object" and all(.[]; type == "string")' "$db_secret_file" >/dev/null ||
  ! jq -r 'to_entries[] | "\(.key)=\(.value)"' "$app_secret_file" >"$app_env_file" ||
  ! jq -r 'to_entries[] | "\(.key)=\(.value)"' "$db_secret_file" >"$db_env_file"; then
  fail "$SECRET_SYNC_FAILURE" "secret_sync_failure"
fi

if ! kubectl -n "$NAMESPACE" create secret generic "$APP_SECRET_NAME" \
  --from-env-file="$app_env_file" --dry-run=client -o yaml |
  kubectl -n "$NAMESPACE" apply -f - >/dev/null 2>&1 ||
  ! kubectl -n "$NAMESPACE" create secret generic "$DB_SECRET_NAME" \
  --from-env-file="$db_env_file" --dry-run=client -o yaml |
  kubectl -n "$NAMESPACE" apply -f - >/dev/null 2>&1; then
  fail "$SECRET_SYNC_FAILURE" "secret_sync_failure"
fi
status "secrets_synchronized"

[[ -d "$MANIFEST_DIR" ]] || fail "$MANIFEST_FAILURE" "manifest_failure"
[[ -f "$MANIFEST_DIR/migration-job.yaml" && -f "$MANIFEST_DIR/app.yaml" ]] ||
  fail "$MANIFEST_FAILURE" "manifest_failure"

previous_image="$(kubectl -n "$NAMESPACE" get deployment "$DEPLOYMENT" \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="app")].image}' 2>/dev/null)" ||
  fail "$CLUSTER_FAILURE" "cluster_failure"
[[ "$previous_image" =~ ^[a-z0-9./_-]+@sha256:[a-f0-9]{64}$ ]] ||
  fail "$CLUSTER_FAILURE" "cluster_failure"

rendered_migration="$(mktemp)"
rendered_app="$(mktemp)"
trap 'rm -f "$app_secret_file" "$db_secret_file" "$app_env_file" "$db_env_file" "$rendered_migration" "$rendered_app"' EXIT
chmod 600 "$rendered_migration" "$rendered_app"
if ! sed "s|__IMAGE__|$IMAGE_REF|g" "$MANIFEST_DIR/migration-job.yaml" >"$rendered_migration" ||
  ! sed "s|__IMAGE__|$IMAGE_REF|g" "$MANIFEST_DIR/app.yaml" >"$rendered_app"; then
  fail "$MANIFEST_FAILURE" "manifest_failure"
fi

if ! kubectl -n "$NAMESPACE" apply -f "$rendered_migration" >/dev/null 2>&1 ||
  ! kubectl -n "$NAMESPACE" wait --for=condition=complete \
    --timeout="${JAPP_MIGRATION_TIMEOUT:-300s}" job/japp-db-migrate >/dev/null 2>&1; then
  status "migration_failed"
  fail "$CLUSTER_FAILURE" "cluster_failure"
fi
status "migration_succeeded"

rollback_application() {
  if ! kubectl -n "$NAMESPACE" set image deployment/"$DEPLOYMENT" \
    "app=$previous_image" >/dev/null 2>&1; then
    return 1
  fi

  kubectl -n "$NAMESPACE" rollout status deployment/"$DEPLOYMENT" \
    --timeout="${JAPP_ROLLOUT_TIMEOUT:-300s}" >/dev/null 2>&1
}

acceptance_failure() {
  local failed_check="$1"
  status "acceptance_failed_${failed_check}"
  if rollback_application; then
    fail "$CLUSTER_FAILURE" "acceptance_failed_rolled_back"
  fi
  fail "$CLUSTER_FAILURE" "acceptance_failed_rollback_failed"
}

if ! kubectl -n "$NAMESPACE" apply -f "$rendered_app" >/dev/null 2>&1 ||
  ! kubectl -n "$NAMESPACE" rollout status deployment/"$DEPLOYMENT" \
    --timeout="${JAPP_ROLLOUT_TIMEOUT:-300s}" >/dev/null 2>&1; then
  status "rollout_failed"
  if rollback_application; then
    fail "$CLUSTER_FAILURE" "cluster_failure_rolled_back"
  fi
  fail "$CLUSTER_FAILURE" "cluster_failure_rollback_failed"
fi
status "rollout_succeeded"

if [[ -z "$PUBLIC_URL" || -z "$EXPECTED_HOSTNAME" ]] ||
  [[ ! "$PUBLIC_URL" =~ ^https://[^/@:]+(:[0-9]+)?(/.*)?$ ]]; then
  acceptance_failure "configuration"
fi
public_hostname="${PUBLIC_URL#https://}"
public_hostname="${public_hostname%%/*}"
public_hostname="${public_hostname%%:*}"
if [[ "$public_hostname" != "$EXPECTED_HOSTNAME" ]]; then
  acceptance_failure "hostname"
fi

response_file="$(mktemp)"
response_headers="$(mktemp)"
trap 'rm -f "$app_secret_file" "$db_secret_file" "$app_env_file" "$db_env_file" "$rendered_migration" "$rendered_app" "$response_file" "$response_headers"' EXIT
chmod 600 "$response_file" "$response_headers"

if ! curl --fail --silent --show-error --location --max-redirs 3 \
  --proto '=https' --tlsv1.2 --max-time "${JAPP_SMOKE_TIMEOUT:-15}" \
  "$PUBLIC_URL/healthz" -o "$response_file" >/dev/null 2>&1 ||
  [[ "$(cat "$response_file" 2>/dev/null)" != "200 OK" ]]; then
  acceptance_failure "healthz"
fi
status "healthz_succeeded"

if ! curl --fail --silent --show-error --location --max-redirs 3 \
  --proto '=https' --tlsv1.2 --max-time "${JAPP_SMOKE_TIMEOUT:-15}" \
  "$PUBLIC_URL/readyz" -o "$response_file" >/dev/null 2>&1 ||
  [[ "$(cat "$response_file" 2>/dev/null)" != "ready" ]]; then
  acceptance_failure "readyz"
fi
status "readyz_succeeded"

gateway_conditions="$(kubectl -n "$NAMESPACE" get gateway japp-gateway \
  -o jsonpath='{range .status.conditions[*]}{.type}={.status}{"\n"}{end}' 2>/dev/null)" || \
  acceptance_failure "gateway"
if ! grep -qx 'Accepted=True' <<<"$gateway_conditions" ||
  ! grep -qx 'Programmed=True' <<<"$gateway_conditions"; then
  acceptance_failure "gateway"
fi

for route in japp japp-http-redirect; do
  route_conditions="$(kubectl -n "$NAMESPACE" get httproute "$route" \
    -o jsonpath='{range .status.parents[*].conditions[*]}{.type}={.status}{"\n"}{end}' 2>/dev/null)" || \
    acceptance_failure "route"
  if ! grep -qx 'Accepted=True' <<<"$route_conditions" ||
    ! grep -qx 'ResolvedRefs=True' <<<"$route_conditions"; then
    acceptance_failure "route"
  fi
done
status "gateway_succeeded"

if ! curl --fail --silent --show-error --max-time "${JAPP_SMOKE_TIMEOUT:-15}" \
  --proto '=https' --tlsv1.2 "$PUBLIC_URL/" -o /dev/null >/dev/null 2>&1; then
  acceptance_failure "certificate"
fi
status "certificate_succeeded"

http_status="$(curl --silent --show-error --max-time "${JAPP_SMOKE_TIMEOUT:-15}" \
  --max-redirs 0 --dump-header "$response_headers" --output /dev/null \
  --write-out '%{http_code}' "http://$EXPECTED_HOSTNAME/" 2>/dev/null)" || \
  acceptance_failure "https_redirect"
if [[ "$http_status" != "301" && "$http_status" != "302" && "$http_status" != "307" && "$http_status" != "308" ]] ||
  ! grep -Eiq "^location: https://$EXPECTED_HOSTNAME(:443)?(/|$)" "$response_headers"; then
  acceptance_failure "https_redirect"
fi
status "https_redirect_succeeded"

status "deployment_succeeded"
