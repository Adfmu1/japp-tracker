# Local Kubernetes deployment

This setup runs the app and PostgreSQL in an existing local Kubernetes cluster.
It does not create a cluster or require cloud infrastructure.

## Deploy

Create a local-only Secret manifest and set a strong, unique password and
`SECRET_KEY`. Use the same database password in `db-secrets` and `DB_URL`.

```sh
cp k8s/secrets.example.yaml k8s/secrets.yaml
```

Build the image and import it into a k3d cluster (replace the cluster name if
needed):

```sh
docker build -t japp:local .
k3d image import japp:local --cluster k3s-default
make deploy-local IMAGE=japp:local
```

For another local Kubernetes distribution, make the image available to its
container runtime, then run `make deploy-local IMAGE=<image>`.

Open the app through a local port-forward:

```sh
kubectl -n japp port-forward service/japp-app 8080:80
```

Then visit <http://127.0.0.1:8080>. The deployment runs the database migration
Job before waiting for the app rollout. PostgreSQL data is stored in a
PersistentVolumeClaim; deleting the PVC deletes the local database data.

To redeploy after changing the app, build and import a new image tag, then pass
that tag through `IMAGE`. Do not reuse a tag with cached local images.

## Deploy with Amazon RDS for PostgreSQL

For a single-node cluster with limited memory, the `rds` overlay deploys only
the app and its ClusterIP service; PostgreSQL runs outside Kubernetes. Create
the `app-secrets` Secret in namespace `japp` with `SECRET_KEY` and a
`DB_URL` that points to the RDS endpoint and enables TLS. The helper prompts
for the RDS password without echoing or saving it, then sends the Secret to the
cluster over SSH:

```sh
python3 scripts/configure-rds-secret.py
```

The RDS CA bundle is mounted into the app and migration containers for
`sslmode=verify-full`. Do not put database credentials in this repository.

Build/import the app image as above, then run:

```sh
make deploy-rds KUBECTL='sudo k0s kubectl' IMAGE=docker.io/library/japp:ec2
```

The target runs the database migration Job against the configured `DB_URL`
before scaling the in-cluster PostgreSQL StatefulSet to zero. Its PVC is
preserved; scaling back to one replica remains possible. Ensure the RDS
security group permits inbound PostgreSQL from the EC2 security group.

## Public HTTPS with Gateway API (temporary IP certificate)

The optional `gateway` setup installs one Traefik replica and uses Kubernetes
Gateway API to route HTTPS to the existing private `japp-app` ClusterIP
Service. Traefik binds host port 443 on the cluster node; no public HTTP
listener is configured. The self-signed certificate is generated locally and
uploaded as a Kubernetes Secret, not stored in this repository.

This temporary certificate covers the EC2 public IPv4 address
`18.199.177.12`, expires after one year, and is not trusted by browsers. Users
will see a warning unless they explicitly trust the certificate. Do not enter
credentials unless you understand and accept that warning. Replace it with a
trusted domain certificate after configuring DNS.

Install the Gateway API Standard CRDs and Traefik (the chart version is pinned):

```sh
kubectl apply -f \
  https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.3/standard-install.yaml
helm repo add traefik https://traefik.github.io/charts
helm repo update
helm upgrade --install traefik traefik/traefik \
  --version 42.4.2 --namespace traefik --create-namespace \
  --values k8s/gateway/traefik-values.yaml
```

Then create the certificate and route:

```sh
make configure-ip-tls KUBECTL='sudo k0s kubectl'
make deploy-gateway-rds KUBECTL='sudo k0s kubectl'
```

After confirming the correct security group and authorization, permit inbound
TCP/443 from `0.0.0.0/0` and keep port 80 closed. This is an intentionally
public IPv4 endpoint.
Verify the Gateway and route become accepted/programmed, then test with:

```sh
curl -kI https://18.199.177.12/
```

`-k` is needed only because the temporary certificate is self-signed. The app
deployment sets `APP_ENV=production`, so session and remember cookies use the
Secure attribute. Gateway resources and the controller are separate from the
RDS application overlay; do not uninstall the controller while the public
route is in use.

### Retire the temporary IP endpoint

Keep the IP endpoint only until the future domain endpoint resolves, passes
normal certificate validation without `-k`, and returns the expected
application response. After all three checks pass, have an authorized operator
remove inbound TCP/443 for this EC2 instance from the correct security group.
Do not make that AWS firewall change as part of applying Kubernetes manifests.
The temporary endpoint is public to all IPv4 sources while enabled; the
self-signed certificate is not an access-control mechanism, and real
credentials must not be entered through a certificate-warning bypass.

`/healthz` is sufficient to verify that traffic reaches Flask, but it does not
check RDS connectivity or migration health.
