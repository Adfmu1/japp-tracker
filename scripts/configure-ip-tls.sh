#!/usr/bin/env bash
set -Eeuo pipefail

PUBLIC_IP="${PUBLIC_IP:-18.199.177.12}"
NAMESPACE="${NAMESPACE:-japp}"
KUBECTL="${KUBECTL:-kubectl}"

if ! python3 -c 'import ipaddress, sys; ipaddress.IPv4Address(sys.argv[1])' "$PUBLIC_IP" >/dev/null 2>&1; then
  echo "PUBLIC_IP must be a valid IPv4 address." >&2
  exit 2
fi

CERT_DIR="$(mktemp -d)"
trap 'rm -rf "$CERT_DIR"' EXIT

openssl req -x509 -nodes -newkey rsa:3072 -sha256 -days 365 \
  -keyout "$CERT_DIR/tls.key" \
  -out "$CERT_DIR/tls.crt" \
  -subj "/CN=$PUBLIC_IP" \
  -addext "subjectAltName=IP:$PUBLIC_IP" \
  -addext "basicConstraints=critical,CA:FALSE" \
  -addext "keyUsage=critical,digitalSignature,keyEncipherment" \
  -addext "extendedKeyUsage=serverAuth"

"$KUBECTL" -n "$NAMESPACE" create secret tls japp-ip-tls \
  --cert="$CERT_DIR/tls.crt" \
  --key="$CERT_DIR/tls.key" \
  --dry-run=client -o yaml |
  "$KUBECTL" apply -f -

echo "Installed self-signed TLS certificate for IP $PUBLIC_IP in namespace $NAMESPACE."
echo "Browsers will display a trust warning; use a domain and trusted certificate for normal use."
