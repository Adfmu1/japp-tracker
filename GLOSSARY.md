# Job Application Tracker

This context covers the job application tracker and the services that make it reachable to users.

## Language

**Public HTTPS endpoint**:
The externally reachable address through which a user connects to the application using HTTPS.

**Trusted HTTPS**:
HTTPS for which the client can validate the server certificate using its normal trust store and the requested hostname.
_Avoid_: Secure connection (when certificate trust has not been established)

**Temporary IP endpoint**:
The interim public HTTPS endpoint addressed by the EC2 instance's public IPv4 address and using a self-signed certificate.
_Avoid_: Production domain endpoint

**Gateway**:
The Kubernetes entry point that receives external application traffic and associates listeners with routes.

**Route**:
A rule that associates traffic received by a Gateway listener with a backend application Service.

**Application Service**:
The private Kubernetes Service that exposes the Flask application to in-cluster components.
