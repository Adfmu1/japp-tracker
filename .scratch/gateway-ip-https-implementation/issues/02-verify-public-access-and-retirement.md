# 02: Verify public access and document endpoint retirement

**What to build:** After an explicitly authorized operator opens TCP/443, verify that an external HTTPS request to the EC2 IP reaches Flask. Document the temporary endpoint's public and untrusted-certificate boundaries, and the conditions and operator steps for retiring it.

**Blocked by:** 01: Configure and validate the temporary HTTPS route

**Status:** ready-for-agent

- [ ] An external HTTPS request to `/healthz` returns the expected Flask response.
- [ ] Documentation states that `/healthz` is database-free and does not verify RDS connectivity or migration health.
- [ ] Documentation states that TCP/443 is publicly reachable from all IPv4 sources and the self-signed certificate must not be bypassed for real credentials.
- [ ] The authorized security-group change remains separate from Kubernetes deployment and opens no TCP/80 listener.
- [ ] The retirement gate requires the future domain endpoint to resolve, pass normal certificate validation, and return the expected app response.
- [ ] The retirement procedure closes TCP/443 ingress for the temporary IP endpoint after the gate passes.
- [ ] Smoke-test output and diagnostics do not expose certificate private keys or application secrets.

**Parent spec:** [Temporary Public HTTPS Endpoint](../../gateway-ip-https/spec.md)
