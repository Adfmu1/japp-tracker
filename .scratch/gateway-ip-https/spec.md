# Temporary Public HTTPS Endpoint

Status: ready-for-agent

## Problem Statement

The RDS-backed job application tracker runs on a single EC2 host in a single-node k0s cluster. The application Service is private, so users cannot currently reach it from outside the cluster. The application needs an interim public entry point while the future domain-based endpoint with a trusted certificate is not yet available.

## Solution

Expose the app through a temporary HTTPS endpoint at the EC2 public IPv4 address `18.199.177.12`. A single Traefik controller uses Kubernetes Gateway API to forward HTTPS requests to the existing private application Service. The endpoint uses a locally generated self-signed certificate, so clients receive encrypted transport but cannot normally validate the server identity through their standard trust store.

The endpoint is public to all IPv4 sources on TCP/443 and is for connectivity verification only. Do not enter real credentials through a certificate-warning bypass. Retire this endpoint only after the future domain endpoint resolves, passes normal certificate validation, and reaches the application; then close the temporary endpoint's security-group ingress.

## User Stories

1. As a user, I want to reach the application at the EC2 public IPv4 address over HTTPS, so that I can verify external connectivity while the domain endpoint is unavailable.
2. As a maintainer, I want the existing application Service to remain private, so that the application is not exposed directly as a public Kubernetes Service.
3. As a maintainer, I want the Gateway to forward requests to the existing application Service, so that the public entry point uses the established application deployment.
4. As a maintainer, I want the endpoint to listen only on HTTPS port 443, so that it does not introduce a public plaintext HTTP listener.
5. As a user, I want the endpoint to use a certificate covering the selected public IPv4 address, so that the certificate represents the address I am visiting.
6. As a user, I want to know that the temporary certificate is self-signed and not normally trusted, so that I do not mistake encrypted transport for verified server identity.
7. As a maintainer, I want the certificate private key to be generated and handled locally without being committed to the repository, so that it is not exposed in source control.
8. As a maintainer, I want HTTPS to be reachable from any IPv4 address on TCP/443, so that external users can verify the application without first configuring an allowlist.
9. As a maintainer, I want Gateway and route readiness to be observable, so that I can distinguish a Kubernetes configuration problem from an application response.
10. As a maintainer, I want an external request to `/healthz` to return the application's expected response, so that the temporary endpoint's routing to Flask can be verified.
11. As a maintainer, I want to understand that `/healthz` is database-free, so that its success is not treated as proof of RDS connectivity or migration health.
12. As a maintainer, I want the Traefik controller to run as one bounded replica, so that its resource use is appropriate for the single-node host.
13. As a maintainer, I want the single-node availability limitation documented, so that the temporary endpoint is not mistaken for a highly available service.
14. As a maintainer, I want the AWS security-group change to remain a separate authorized operator action, so that Kubernetes deployment does not silently change the public network boundary.
15. As a maintainer, I want the temporary endpoint retired only after the domain endpoint is externally verified with a normally trusted certificate and a successful application response, so that users are not left without a working endpoint.
16. As a maintainer, I want TCP/443 ingress for the temporary endpoint closed after retirement, so that the obsolete public endpoint is no longer reachable.

## Implementation Decisions

- The temporary endpoint uses the EC2 public IPv4 address `18.199.177.12`.
- A single Traefik controller provides the external entry point using Kubernetes Gateway API.
- The application remains behind its existing private ClusterIP Service.
- The Gateway exposes HTTPS on TCP/443 only; no public HTTP listener is configured.
- A self-signed certificate with the public IPv4 address in its IP subject alternative name is used temporarily. It is not normally trusted by browsers or other standard clients.
- Certificate generation occurs locally, and the private key is not stored in the repository.
- Public ingress is intentionally available to all IPv4 sources. The certificate warning is not an access-control mechanism.
- Opening inbound TCP/443 in the EC2 security group is an independent operator action requiring appropriate authorization and confirmation of the target security group. No deployment target opens the port automatically.
- The controller runs as one replica with bounded resource requests and limits. Loss of the EC2 node makes the endpoint unavailable.
- `/healthz` is the external smoke-test path. Its success proves that the request reached the Flask application; it does not prove database connectivity because the endpoint is database-free.
- The domain-based endpoint with a normally trusted certificate is separate work. The temporary endpoint is retired after the domain endpoint resolves, passes normal TLS certificate validation, and returns the expected application response; retirement includes closing this endpoint's security-group ingress.
- This temporary endpoint is for connectivity verification. Real credentials must not be entered through a self-signed-certificate warning bypass.

## Testing Decisions

- Prefer the highest seam: externally request the temporary IP endpoint's `/healthz` and assert the expected application response.
- Before external verification, confirm the Kubernetes Gateway reports accepted/programmed and the HTTPRoute is accepted and attached to the intended listener.
- Validate the Traefik chart configuration and Gateway/HTTPRoute manifests against the pinned chart and Gateway API schemas before applying them.
- Verify the generated certificate contains the selected IPv4 address in its IP subject alternative name and has server-auth usage; do not assert that standard clients trust it.
- Verify certificate-generation behavior does not leave the private key in the repository or a persistent temporary location.
- Verify the public listener is HTTPS-only and routes only to the existing private application Service.
- Treat `/healthz` as routing/application evidence only. Database health, migration success, and production readiness require their own checks.
- Test the retirement gate by verifying that retirement is not considered complete until the domain resolves, normal certificate validation succeeds, and the application response is correct; then verify that the temporary ingress is closed.
- Existing repository prior art includes Python linting/format checks and HTTP smoke checks, but there are no established Kubernetes manifest tests or automated external browser tests. Add focused manifest/render checks for this configuration rather than introducing a broad test framework.
- Tests and diagnostics must not print private key material, database credentials, session secrets, or other secret values.

## Out of Scope

- Registering or configuring the future domain and DNS records.
- Obtaining or configuring a normally trusted certificate for the domain endpoint.
- Deploying the future domain endpoint or migrating user traffic to it.
- Changing the application's authentication, registration, or authorization behavior.
- Proving RDS availability, database readiness, or migration success via `/healthz`.
- High availability, multiple controller replicas, multiple EC2 nodes, or load balancing across nodes.
- Automatically changing the EC2 security group or modifying AWS resources as part of Kubernetes deployment.
- Public HTTP, HTTP-to-HTTPS redirects, or opening TCP/80.
- Committing, distributing, or manually installing the self-signed certificate as a trusted root.

## Further Notes

- A self-signed certificate can encrypt traffic while failing normal identity validation. Users must not interpret HTTPS alone as proof that they reached the intended server.
- The endpoint is intentionally public. Keep the application's normal authentication and security controls in force; do not use certificate-warning bypasses for real credentials.
- The production deployment plan already describes a separate domain-based HTTPS endpoint. This spec does not replace or revise that work.
- No Git commit is authorized by this spec or the handoff.
