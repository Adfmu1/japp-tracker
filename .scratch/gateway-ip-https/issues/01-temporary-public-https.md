# 01: Expose the application through a temporary public HTTPS endpoint

**What to build:** A temporary HTTPS endpoint at the EC2 public IPv4 address `18.199.177.12`, using Traefik and Gateway API to route to the existing private app Service. The endpoint uses a self-signed certificate and is publicly reachable from all IPv4 sources on TCP/443. It is for connectivity verification only; do not enter real credentials through a certificate-warning bypass.

**Status:** ready-for-agent

- [ ] The application Service remains private and the Gateway routes HTTPS traffic to it.
- [ ] The public listener uses TCP/443 with HTTPS only; TCP/80 is not opened or served.
- [ ] The locally generated self-signed certificate covers the selected IP and its private key is not committed or persisted outside the intended Kubernetes Secret workflow.
- [ ] Traefik runs as one bounded replica, and the single-node availability limitation is documented.
- [ ] Gateway and HTTPRoute conditions show the Gateway programmed and route accepted/attached to the intended listener.
- [ ] An external HTTPS request to `/healthz` returns the expected Flask response.
- [ ] Documentation states that `/healthz` is database-free and does not demonstrate RDS or migration health.
- [ ] EC2 security-group ingress on TCP/443 is a separate, explicitly authorized operator action; deployment does not modify it.
- [ ] The retirement gate requires the future domain endpoint to resolve, pass normal certificate validation, and return the expected app response.
- [ ] Retirement closes the temporary endpoint's TCP/443 security-group ingress.
- [ ] Validation and diagnostics do not expose certificate private keys or application secrets.

**Spec:** [Temporary Public HTTPS Endpoint](../spec.md)
