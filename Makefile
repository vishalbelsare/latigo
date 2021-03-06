SHELL:=/bin/bash
ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
LATIGO_VERSION:=$(shell cat app/VERSION)
APP_DIR:="${ROOT_DIR}/app"
TESTS_DIR:="${ROOT_DIR}/tests"
CODE_QUALITY_DIR:="${ROOT_DIR}/code_quality"
GORDO_CLUSTER_NAME:="ioc07jsv"
LATIGO_CLUSTER_NAME:="aurora15"
CLUSTER_SUBSCRIPTION="019958ea-fe2c-4e14-bbd9-0d2db8ed7cfc"
COMPUTED_ENV="${ROOT_DIR}/set_env.py"
LATIGO_BASE_IMAGE_NAME:="latigo-base"
LATIGO_BASE_IMAGE_RELEASE_NAME:="${LATIGO_BASE_IMAGE_NAME}:${LATIGO_VERSION}"

LATIGO_PRODUCTION_BRANCH:="master"
LATIGO_STAGE_BRANCH:="stage"
GITHUB_BRANCH:=$(patsubst refs/heads/%,%,${GITHUB_REF})
GITHUB_TAG:=$(patsubst refs/tags/%,%,${GITHUB_REF})

.PHONY: all code-quality tests_all tests_unit tests_integration set-env setup up rebuild-req

all: help

info:  ## Show info about env and used variables
	@echo "LATIGO_VERSION=${LATIGO_VERSION}"
	@echo "ROOT_DIR=${ROOT_DIR}"
	@echo "APP_DIR=${APP_DIR}"
	@echo "TESTS_DIR=${TESTS_DIR}"
	@echo "CODE_QUALITY_DIR=${CODE_QUALITY_DIR}"
	@echo "SHELL=${SHELL}"
	@echo "LATIGO_PRODUCTION_BRANCH=${LATIGO_PRODUCTION_BRANCH}"
	@echo "LATIGO_STAGE_BRANCH=${LATIGO_STAGE_BRANCH}"
	@echo "GORDO_CLUSTER_NAME=${GORDO_CLUSTER_NAME}"
	@echo "LATIGO_CLUSTER_NAME=${LATIGO_CLUSTER_NAME}"
	@echo "GITHUB_REF=${GITHUB_REF}"
	@echo "GITHUB_BRANCH=${GITHUB_BRANCH}"
	@echo "GITHUB_TAG=${GITHUB_TAG}"
	@echo "LATIGO_BASE_IMAGE_NAME=${LATIGO_BASE_IMAGE_NAME}"
	@echo "LATIGO_BASE_IMAGE_RELEASE_NAME=${LATIGO_BASE_IMAGE_RELEASE_NAME}"

	@echo "DOCKER_REGISTRY=${DOCKER_REGISTRY}"
	@echo "DOCKER_REPO=${DOCKER_REPO}"
	@echo "DOCKER_USERNAME=${DOCKER_USERNAME}"
	@echo "DOCKER_PASSWORD=NOT SHOWN"

code-quality:  ## Run code quality tools
	cd "${CODE_QUALITY_DIR}" && make all

show-env:  ## Show the variables related to Latigo in the current environment
	env | sort

compose_requirements:  ## run pip-compile for requirements.in and test_requirements.in
	pip install --upgrade pip
	pip install --upgrade pip-tools
	pip-compile --output-file=requirements.txt requirements.in
	pip-compile --output-file=test_requirements.txt test_requirements.inpip

install_app_requirements:  ## install requirements for app and tests run
	pip install --upgrade pip
	pip install --upgrade pip-tools
	cd app && pip install -r requirements.txt
	cd app && pip install -r test_requirements.txt

setup:  ## Rebuild latest latigo and install it to site-packages
	rm -rf app/build
	pip uninstall -y latigo
	pip install -e app/


############### Convenience access ######################

login-azure:  ## Login to azure
	az login
	az account set --subscription $(CLUSTER_SUBSCRIPTION)
	az account show

login-gordo:  ## Login to gordo cluster
	az aks get-credentials --overwrite-existing --resource-group ${GORDO_CLUSTER_NAME} --name ${GORDO_CLUSTER_NAME}
	kubectl config set-context --current --namespace=kubeflow
	kubectl get gordos

login-latigo:  ## Login to latigo cluster
	az aks get-credentials --overwrite-existing --resource-group ${LATIGO_CLUSTER_NAME} --name ${LATIGO_CLUSTER_NAME}
	kubectl config set-context --current --namespace=latigo
	kubectl get all

login-docker:  ## Login to docker hub
	echo "Logging in to docker registry ${DOCKER_USERNAME}@${DOCKER_REGISTRY}...";\
	echo "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USERNAME}" --password-stdin "${DOCKER_REGISTRY}";\
	if [ $$? -eq 0 ]; then\
		echo "Logging in to docker registry ${DOCKER_USERNAME}@${DOCKER_REGISTRY}: OK";\
	else\
		echo "Logging in to docker registry ${DOCKER_USERNAME}@${DOCKER_REGISTRY}: Failed";\
		exit 1;\
	fi\

list-gordos:  ## List available projects in gordo
	kubectl get gordos

port-forward:  ##  Set up port forwarding to access gordo via localhost:8888
	while : ; do printf "PORTFORWARDING----\n"; kubectl port-forward svc/ambassador -n ambassador 8888:80; done

############### Convenience docker compose ####################

docker-build: setup code-quality tests show-env login-docker
	eval $(./set_env.py) && docker-compose -f docker-compose.yml build --parallel --pull --compress

docker-prep-data:
	# NOTE: The volumes folder must not be inside the context of any docker or the docker builds will fail!
	sudo mkdir -p ../volumes/latigo/influxdb/data
	sudo mkdir -p ../volumes/latigo/grafana/data
	sudo chown 472:472 ../volumes/latigo/grafana/data

up: docker-build
	eval $(./set_env.py) && docker-compose up --remove-orphans --quiet-pull --no-build --force-recreate
	docker ps -a

up-dev:
	eval $(./set_env.py) && docker-compose up --remove-orphans
	docker ps -a

down:  ## Stops containers and removes containers, networks, volumes, and images created by `up`
	docker-compose down
	docker ps -a

############### Tests ####################
tests_all:  ## Run all tests with coverage
	py.test --cov=app -vv tests

tests_unit:  ##  Run unit tests
	py.test --cov=app -vv tests/unit

tests_integration:  ##  Run integration tests
	py.test --cov=app -vv tests/integration


############### Build docker images ####################
build:  ## Build Latigo image
	@echo "Building master branch image"
	docker build --compress --force-rm . -f Dockerfile -t "${LATIGO_BASE_IMAGE_NAME}" -t "${LATIGO_BASE_IMAGE_RELEASE_NAME}"


############### Scan docker images ####################
scan:  ## Scan images for vulnerabilities
	@uname_S=$(shell uname -s 2>/dev/null || echo not); \
	trivy=$(shell which trivy); \
	if [ -z "$$trivy" ]; then \
		if [ "$$uname_S" == 'Darwin' ]; then \
			machine="macOS"; \
		elif [ "$$uname_S"  == 'Linux' ]; then \
			machine="Linux"; \
		else \
			echo "Unable to determine platform '$$uname_S'"; exit 1; \
		fi; \
		TRIVY_VERSION=$(shell curl --silent "https://api.github.com/repos/aquasecurity/trivy/releases/latest" | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/'); \
		echo "Downloading trivy.."; \
		[ -n "$$TRIVY_VERSION" ] && [ -n "$$machine" ] && curl -Ls "https://github.com/aquasecurity/trivy/releases/download/v$${TRIVY_VERSION}/trivy_$${TRIVY_VERSION}_$${machine}-64bit.tar.gz" | tar zx --wildcards '*trivy' || { echo "Download or extract failed for '$${machine}' version '$${TRIVY_VERSION}'."; exit 1; }; \
		trivy="./trivy"; \
	else \
		TRIVY_VERSION=$(shell trivy -v 2>/dev/null | head -1 | cut -d ' ' -f 2); \
	fi; \
	echo "Trivy version is $${TRIVY_VERSION} and platform is $${uname_S}"; \
	$$trivy --clear-cache && $$trivy --exit-code 1 -severity HIGH,CRITICAL --light --no-progress --ignore-unfixed ${LATIGO_BASE_IMAGE_NAME}:latest


############### Push docker images ####################
push:  ## Push image
	echo "Pushing image '${LATIGO_BASE_IMAGE_NAME}' with version '${LATIGO_VERSION}'";\
	bash -x deploy/docker_push.sh ${LATIGO_BASE_IMAGE_NAME} ${LATIGO_BASE_IMAGE_NAME} ${LATIGO_VERSION}

############### Docker cleanup ####################
prune:  ## Prune docker
	docker system prune -a


############### Secrets management ####################
get-secrets:  ## Get prod secrets
	az keyvault secret show --name "latigo-executor-config-yaml" --vault-name "gordo-vault" --query value --output tsv > ./executor_secret.yaml
	az keyvault secret show --name "latigo-scheduler-config-yaml" --vault-name "gordo-vault" --query value --output tsv > ./scheduler_secret.yaml

set-secrets:  ## Set prod secrets
	az keyvault secret set --name "latigo-executor-config-yaml" --vault-name "gordo-vault" --file ./executor_secret.yaml  --encoding utf-8
	az keyvault secret set --name "latigo-scheduler-config-yaml" --vault-name "gordo-vault" --file ./scheduler_secret.yaml  --encoding utf-8


############### Help ####################
help: ## Show this help
	@egrep '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
