# 01: Configure and validate the temporary HTTPS route

**What to build:** A bounded Traefik Gateway routes HTTPS for the EC2 public IPv4 address to the existing private application Service using the temporary self-signed certificate. The route can be verified inside the cluster without changing AWS ingress.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Traefik runs as one bounded replica and listens for HTTPS on TCP/443 only.
- [ ] The Gateway and HTTPRoute route traffic to the existing private application Service.
- [ ] The locally generated certificate covers the selected IP and is used by the Gateway without committing its private key.
- [ ] Gateway and HTTPRoute status conditions confirm the listener is programmed and the route is accepted and attached.
- [ ] The pinned Traefik chart configuration and Gateway API manifests pass local render/schema validation.
- [ ] The EC2 security group is not modified by deployment automation.

**Parent spec:** [Temporary Public HTTPS Endpoint](../../gateway-ip-https/spec.md)
