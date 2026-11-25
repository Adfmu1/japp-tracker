# Temporary IP endpoint retirement

Retire this endpoint only after all of the following are verified from an
external client:

1. The production domain resolves to the domain endpoint.
2. HTTPS succeeds without a certificate-validation bypass.
3. A request to the domain endpoint's `/healthz` returns the expected Flask
   response.

Then perform the retirement with an operator authorized to change the EC2
security group:

1. Remove inbound TCP/443 for the temporary EC2 endpoint from the confirmed
   security group. This AWS change is separate from Kubernetes deployment.
2. From an external network, confirm that a request to
   `https://18.199.177.12/healthz` can no longer establish a connection.
3. Delete the temporary route and certificate Secret in namespace `japp`.
4. Uninstall the Traefik Helm release only if it is dedicated to this Gateway
   and no other active route depends on it.
5. Confirm that the domain endpoint still serves the expected application
   response and that the RDS-backed application resources remain in place.

Do not remove the application Service or RDS resources as part of retiring the
temporary endpoint. The self-signed certificate warning is not an access
control mechanism; do not enter real credentials through a warning bypass
while the endpoint remains available.
