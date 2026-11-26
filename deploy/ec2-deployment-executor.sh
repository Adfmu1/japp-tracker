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

status() {
  printf 'deployment_status=%s\n' "$1"
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
readonly COSIGN_IDENTITY="${COSIGN_CERTIFICATE_IDENTITY:?COSIGN_CERTIFICATE_IDENTITY is required}"
readonly COSIGN_ISSUER="${COSIGN_OIDC_ISSUER:?COSIGN_OIDC_ISSUER is required}"

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
  fail "$CLUSTER_FAILURE" "cluster_failure"
fi
status "migration_succeeded"

if ! kubectl -n "$NAMESPACE" apply -f "$rendered_app" >/dev/null 2>&1 ||
  ! kubectl -n "$NAMESPACE" rollout status deployment/"$DEPLOYMENT" \
    --timeout="${JAPP_ROLLOUT_TIMEOUT:-300s}" >/dev/null 2>&1; then
  kubectl -n "$NAMESPACE" set image deployment/"$DEPLOYMENT" \
    "app=$previous_image" >/dev/null 2>&1 || true
  kubectl -n "$NAMESPACE" rollout status deployment/"$DEPLOYMENT" \
    --timeout="${JAPP_ROLLOUT_TIMEOUT:-300s}" >/dev/null 2>&1 || true
  fail "$CLUSTER_FAILURE" "cluster_failure_rolled_back"
fi
status "rollout_succeeded"

if [[ -n "${JAPP_PUBLIC_URL:-}" ]] &&
  ! curl --fail --silent --show-error --max-time "${JAPP_SMOKE_TIMEOUT:-15}" \
    "$JAPP_PUBLIC_URL/healthz" >/dev/null 2>&1; then
  kubectl -n "$NAMESPACE" set image deployment/"$DEPLOYMENT" \
    "app=$previous_image" >/dev/null 2>&1 || true
  kubectl -n "$NAMESPACE" rollout status deployment/"$DEPLOYMENT" \
    --timeout="${JAPP_ROLLOUT_TIMEOUT:-300s}" >/dev/null 2>&1 || true
  fail "$CLUSTER_FAILURE" "cluster_failure_rolled_back"
fi

status "deployment_succeeded"
