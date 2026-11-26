VENV   := .venv
PYTHON := python3
PIP    := $(VENV)/bin/pip
FLASK  := $(VENV)/bin/flask
RUFF   := $(VENV)/bin/ruff
KUBECTL ?= kubectl
NAMESPACE ?= japp
IMAGE ?= docker.io/adfmu/japp:v1

.PHONY: run venv install lint format fix deploy-local deploy-rds deploy-gateway-rds

run:
	$(FLASK) run --port 5095

venv:
	$(PYTHON) -m venv $(VENV)

install:
	@test -d $(VENV) || $(MAKE) venv
	$(PIP) install -r requirements.txt

lint:
	$(RUFF) check .
	$(RUFF) format --check .

format:
	$(RUFF) format .

fix:
	$(RUFF) check --fix .
	$(RUFF) format .

deploy-local:
	@set -Eeuo pipefail; \
	$(KUBECTL) apply -f k8s/namespace.yaml; \
	if [ -f k8s/secrets.yaml ]; then \
		$(KUBECTL) -n $(NAMESPACE) apply -f k8s/secrets.yaml; \
	else \
		echo "Using existing local app-secrets and db-secrets."; \
		$(KUBECTL) -n $(NAMESPACE) get secret app-secrets >/dev/null; \
		$(KUBECTL) -n $(NAMESPACE) get secret db-secrets >/dev/null; \
	fi; \
	$(KUBECTL) kustomize k8s/local --load-restrictor LoadRestrictionsNone \
		| sed 's#docker.io/adfmu/japp:v1#$(IMAGE)#g' \
		| $(KUBECTL) apply -f -; \
	$(KUBECTL) -n $(NAMESPACE) rollout status statefulset/postgres --timeout=180s; \
	$(KUBECTL) -n $(NAMESPACE) delete job/japp-db-migrate --ignore-not-found; \
	$(KUBECTL) kustomize k8s/local-migration --load-restrictor LoadRestrictionsNone \
		| sed 's#docker.io/adfmu/japp:v1#$(IMAGE)#g' \
		| $(KUBECTL) apply -f -; \
	if ! $(KUBECTL) -n $(NAMESPACE) wait --for=condition=complete job/japp-db-migrate --timeout=360s; then \
		$(KUBECTL) -n $(NAMESPACE) describe job/japp-db-migrate; \
		$(KUBECTL) -n $(NAMESPACE) logs job/japp-db-migrate --all-containers=true --tail=200 || true; \
		exit 1; \
	fi; \
	$(KUBECTL) -n $(NAMESPACE) rollout status deployment/japp-app --timeout=180s

deploy-rds:
	@set -Eeuo pipefail; \
	$(KUBECTL) apply -f k8s/namespace.yaml; \
	$(KUBECTL) -n $(NAMESPACE) get secret app-secrets >/dev/null; \
	$(KUBECTL) kustomize k8s/rds --load-restrictor LoadRestrictionsNone \
		| sed 's#docker.io/adfmu/japp:v1#$(IMAGE)#g' \
		| $(KUBECTL) apply -f -; \
	$(KUBECTL) -n $(NAMESPACE) delete job/japp-db-migrate --ignore-not-found; \
	$(KUBECTL) kustomize k8s/local-migration --load-restrictor LoadRestrictionsNone \
		| sed 's#docker.io/adfmu/japp:v1#$(IMAGE)#g' \
		| $(KUBECTL) apply -f -; \
	if ! $(KUBECTL) -n $(NAMESPACE) wait --for=condition=complete job/japp-db-migrate --timeout=360s; then \
		$(KUBECTL) -n $(NAMESPACE) describe job/japp-db-migrate; \
		$(KUBECTL) -n $(NAMESPACE) logs job/japp-db-migrate --all-containers=true --tail=200 || true; \
		exit 1; \
	fi; \
	$(KUBECTL) -n $(NAMESPACE) scale statefulset/postgres --replicas=0; \
	$(KUBECTL) -n $(NAMESPACE) rollout status deployment/japp-app --timeout=180s

deploy-gateway-rds:
	@set -Eeuo pipefail; \
	$(KUBECTL) apply -f k8s/gateway/route.yaml
