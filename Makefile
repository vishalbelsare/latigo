SHELL:=/bin/bash
ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
LATIGO_VERSION:=$(shell cat app/VERSION)
APP_DIR:="${ROOT_DIR}/app"
TESTS_DIR:="${ROOT_DIR}/tests"
CODE_QUALITY_DIR:="${ROOT_DIR}/code_quality"
GORDO_CLUSTER_NAME:="ioc07jsv"
LATIGO_CLUSTER_NAME:="aurora48"
CLUSTER_SUBSCRIPTION="019958ea-fe2c-4e14-bbd9-0d2db8ed7cfc"
COMPUTED_ENV="${ROOT_DIR}/set_env.py"
LATIGO_BASE_IMAGE_NAME:="latigo-base"
LATIGO_BASE_IMAGE_RELEASE_NAME:="${LATIGO_BASE_IMAGE_NAME}:${LATIGO_VERSION}"
LATIGO_BASE_IMAGE_STAGE_NAME:="${LATIGO_BASE_IMAGE_NAME}:${LATIGO_VERSION}rc"

LATIGO_PRODUCTION_BRANCH:="master"
LATIGO_STAGE_BRANCH:="stage"
GITHUB_BRANCH:=$(patsubst refs/heads/%,%,${GITHUB_REF})
GITHUB_TAG:=$(patsubst refs/tags/%,%,${GITHUB_REF})

.PHONY: all code-quality test set-env setup up rebuild-req

all: help

info:
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
	@echo "LATIGO_BASE_IMAGE_STAGE_NAME=${LATIGO_BASE_IMAGE_STAGE_NAME}"

	@echo "DOCKER_REGISTRY=${DOCKER_REGISTRY}"
	@echo "DOCKER_REPO=${DOCKER_REPO}"
	@echo "DOCKER_USERNAME=${DOCKER_USERNAME}"
	@echo "DOCKER_PASSWORD=NOT SHOWN"

code-quality:
	cd "${CODE_QUALITY_DIR}" && make all

tests:
	cd "${TESTS_DIR}" && make all

tests_unit:
	# TODO enable all the tests and replace this command
	cd "${TESTS_DIR}" && make utils && make scheduler

tests_integration:
	cd "${TESTS_DIR}" && make integration_metadata_api

show-env:
	env | sort

pgsql-perm :
	sudo mkdir "${ROOT_DIR}/volumes/postgres" -p && sudo chown -R lroll:lroll "${ROOT_DIR}/volumes/postgres"

req:
	pip install --upgrade pip
	pip uninstall gordo -y
	pip install --upgrade pip-tools
	cd app && cat requirements.in | sort -u > r.in
	cd app && pip-compile --output-file=requirements.txt r.in
	cd app && cat requirements.in, test_requirements.in | sort -u > r.in
	cd app && pip-compile --output-file=test_requirements.txt r.in
	[ ! -e r.in ] || rm r.in
	cd app && pip install -r requirements.txt
	cd app && pip install -r test_requirements.txt

# Rebuild latest latigo and install it to site-packages
setup:
	rm -rf app/build
	pip uninstall -y latigo
	pip install -e app/

build-docs:
	@echo "PLACEHOLDER: LATIGO MAKEFILE IS BUILDING DOCUMENTATION"
	@sleep 1

############### Convenience access ######################

login-azure:
	az login
	az account set --subscription $(CLUSTER_SUBSCRIPTION)
	az account show

login-gordo:
	az aks get-credentials --overwrite-existing --resource-group ${GORDO_CLUSTER_NAME} --name ${GORDO_CLUSTER_NAME} --admin
	kubectl config set-context --current --namespace=kubeflow
	kubectl get gordos

login-latigo:
	az aks get-credentials --overwrite-existing --resource-group ${LATIGO_CLUSTER_NAME} --name ${LATIGO_CLUSTER_NAME} --admin
	kubectl config set-context --current --namespace=latigo
	kubectl get all

login-docker:
	echo "Logging in to docker registry ${DOCKER_USERNAME}@${DOCKER_REGISTRY}...";\
	echo "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USERNAME}" --password-stdin "${DOCKER_REGISTRY}";\
	if [ $$? -eq 0 ]; then\
		echo "Logging in to docker registry ${DOCKER_USERNAME}@${DOCKER_REGISTRY}: OK";\
	else\
		echo "Logging in to docker registry ${DOCKER_USERNAME}@${DOCKER_REGISTRY}: Failed";\
		exit 1;\
	fi\

list-gordos:
	kubectl get gordos

port-forward:
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

down:
	docker-compose down
	docker ps -a

############### Build docker images ####################


build:
	@if [ "$(LATIGO_PRODUCTION_BRANCH)" == "${GITHUB_BRANCH}" ]; then\
		echo "Building master branch for base";\
		docker build . -f Dockerfile.base -t "${LATIGO_BASE_IMAGE_NAME}" -t "${LATIGO_BASE_IMAGE_RELEASE_NAME}";\
	elif [ "$(LATIGO_STAGE_BRANCH)" == "${GITHUB_BRANCH}" ]; then\
		echo "Building stage branch for base";\
		docker build . -f Dockerfile.base -t "${LATIGO_BASE_IMAGE_NAME}" -t "${LATIGO_BASE_IMAGE_STAGE_NAME}" -t "${LATIGO_BASE_IMAGE_NAME}:tag${GITHUB_TAG}";\
	else\
		echo "Unknown branch!";\
		docker build . -f Dockerfile.base -t "${LATIGO_BASE_IMAGE_NAME}";\
	fi;\


############### Push docker images ####################


push:
	export DOCKER_NAME=${LATIGO_BASE_IMAGE_NAME};\
	export DOCKER_IMAGE=${LATIGO_BASE_IMAGE_NAME};\
	echo "Pushing imge ${DOCKER_NAME}";\
	bash -x deploy/docker_push.sh

############### Docker cleanup ####################

prune:
	docker system prune -a


############### Secrets management ####################

get-secrets:
	az keyvault secret show --name "latigo-executor-config-yaml" --vault-name "gordo-vault" --query value --output tsv > ./executor_secret.yaml
	az keyvault secret show --name "latigo-scheduler-config-yaml" --vault-name "gordo-vault" --query value --output tsv > ./scheduler_secret.yaml

set-secrets:
	az keyvault secret set --name "latigo-executor-config-yaml" --vault-name "gordo-vault" --file ./executor_secret.yaml  --encoding utf-8
	az keyvault secret set --name "latigo-scheduler-config-yaml" --vault-name "gordo-vault" --file ./scheduler_secret.yaml  --encoding utf-8



############### Help ####################

help:
	@echo "#############################################"
	@echo "# This is a conveneince Makefile for Latigo #"
	@echo "#############################################"
	@echo ""
	@echo " General targets:"
	@echo ""
	@echo " + make help             Show this help"
	@echo " + make code-quality     Run code quality tools"
	@echo " + make tests            Run (almost) all tests. NOTE: For more options see tests/Makefile"
	@echo " + make show-env         Show the variables related to Latigo in the current environment"
	@echo " + make pgsql-perm       Set up permissions of the postgres docker image's volume (necessary nuisance)"
	@echo " + make req              Rebuild pinned versions in *requirements.txt from *requirements.in"
	@echo " + make setup            Build latigo pip package"
	@echo ""
	@echo " Cluster targets:"
	@echo ""
	@echo " + login-gordo           Login to gordo cluster"
	@echo " + login-latigo          Login to latigo cluster"
	@echo " + login-azure           Login to azure"
	@echo " + list-gordos           List available projects in gordo"
	@echo " + port-forward          Set up port forwarding to access gordo via localhost:8888"
	@echo ""
	@echo " Development targets:"
	@echo ""
	@echo " + make help             Show this help"
	@echo " + make up               Build incrementally, test and run all from scratch"
	@echo " + make up-dev           Same as up but faster (for development)"
	@echo " + make down             Shutdown docker images"
	@echo ""
	@echo " Deployment targets:"
	@echo ""
	@echo " + make build            Build all docker images"
	@echo " + make push             Build and push all docker images"
	@echo " + prune                 Clean up old docker resources locally"
	@echo ""
	@echo " Advanced targets:"
	@echo ""
	@echo " + make set-secrets      Push secrets to azure key vault (ADVANCED)"
	@echo " + make get-secrets      Show secrets from azure key vault (ADVANCED)"
	@echo ""

