ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
LATIGO_VERSION:=$(shell cat VERSION)
APP_DIR:="${ROOT_DIR}/app"
TESTS_DIR:="${ROOT_DIR}/tests"
CODE_QUALITY_DIR:="${ROOT_DIR}/code_quality"
SHELL:=/bin/bash
CLUSTER_NAME:="ioc48jsv"
CLUSTER_SUBSCRIPTION="019958ea-fe2c-4e14-bbd9-0d2db8ed7cfc"
COMPUTED_ENV="${ROOT_DIR}/set_env.py"
LATIGO_SCHEDULER_IMAGE_NAME:="latigo-scheduler"
LATIGO_EXECUTOR_IMAGE_NAME:="latigo-executor"
LATIGO_SCHEDULER_IMAGE_RELEASE_NAME:="${LATIGO_SCHEDULER_IMAGE_NAME}:${LATIGO_VERSION}"
LATIGO_SCHEDULER_IMAGE_STAGE_NAME:=${LATIGO_SCHEDULER_IMAGE_NAME}:${LATIGO_VERSION}rc
LATIGO_EXECUTOR_IMAGE_RELEASE_NAME:="${LATIGO_EXECUTOR_IMAGE_NAME}:${LATIGO_VERSION}"
LATIGO_EXECUTOR_IMAGE_STAGE_NAME:="${LATIGO_EXECUTOR_IMAGE_NAME}:${LATIGO_VERSION}rc"
LATIGO_PRODUCTION_BRANCH:="master"
LATIGO_STAGE_BRANCH:="stage"



.PHONY: all code-quality tests set-env postgres-permission setup up rebuild-req

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
	@echo "CLUSTER_NAME=${CLUSTER_NAME}"
	@echo "CIRCLE_BRANCH=${CIRCLE_BRANCH}"
	@echo "CIRCLE_TAG=${CIRCLE_TAG}"
	@echo "LATIGO_SCHEDULER_IMAGE_NAME=${LATIGO_SCHEDULER_IMAGE_NAME}"
	@echo "LATIGO_EXECUTOR_IMAGE_NAME=${LATIGO_EXECUTOR_IMAGE_NAME}"
	@echo "LATIGO_SCHEDULER_IMAGE_RELEASE_NAME=${LATIGO_SCHEDULER_IMAGE_RELEASE_NAME}"
	@echo "LATIGO_SCHEDULER_IMAGE_STAGE_NAME=${LATIGO_SCHEDULER_IMAGE_STAGE_NAME}"
	@echo "LATIGO_EXECUTOR_IMAGE_RELEASE_NAME=${LATIGO_EXECUTOR_IMAGE_RELEASE_NAME}"
	@echo "LATIGO_EXECUTOR_IMAGE_STAGE_NAME=${LATIGO_EXECUTOR_IMAGE_STAGE_NAME}"

code-quality:
	cd "${CODE_QUALITY_DIR}" && make all

test:
	cd "${TESTS_DIR}" && make all

show-env:
	env | grep -i latigo

pgsql-perm :
	sudo mkdir "${ROOT_DIR}/volumes/postgres" -p && sudo chown -R lroll:lroll "${ROOT_DIR}/volumes/postgres"

req:
	pip install --upgrade pip
	pip uninstall gordo-components -y
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
	pip install app/

build-docs:
	@echo "PLACEHOLDER: LATIGO MAKEFILE IS BUILDING DOCUMENTATION"
	@sleep 1

############### Convenience gordo access ######################


login-gordo:
	az login
	az account set --subscription $(CLUSTER_SUBSCRIPTION)
	az account show
	az aks get-credentials --overwrite-existing --resource-group ${CLUSTER_NAME} --name ${CLUSTER_NAME} --admin
	kubectl config set-context --current --namespace=kubeflow
	kubectl get gordos

list-gordos:
	kubectl get gordos

port-forward:
	while : ; do printf "PORTFORWARDING----\n"; kubectl port-forward svc/ambassador -n ambassador 8888:80; done

############### Convenience docker compose ####################

build: postgres-permission setup code-quality tests show-env
	docker-compose build --parallel --pull --compress

up: build
	# NOTE: The volumes folder must not be inside the context of any docker or the docker builds will fail!
	sudo mkdir -p ../volumes/latigo/influxdb/data
	sudo mkdir -p ../volumes/latigo/grafana/data
	sudo chown 472:472 ../volumes/latigo/grafana/data
	eval $(./set_env.py) && docker-compose up --remove-orphans --quiet-pull --no-build
	docker ps -a

down:
	docker-compose down
	docker ps -a

influxdb:
	eval $(./set_env.py) && docker-compose up --build -d influxdb
	docker-compose logs -f influxdb

grafana:
	eval $(./set_env.py) && docker-compose up --build -d grafana
	docker-compose logs -f grafana

postgres:
	eval $(./set_env.py) && docker-compose up --build -d postgres
	docker-compose logs -f postgres

adminer:
	eval $(./set_env.py) && docker-compose up --build -d adminer
	docker-compose logs -f adminer

scheduler: build
	eval $(./set_env.py) && docker-compose up --build -d latigo-scheduler
	docker-compose logs -f latigo-scheduler

executor: build
	eval $(./set_env.py) && docker-compose up --build -d latigo-executor-1
	docker-compose logs -f latigo-executor-1

############### Build docker images ####################


build-scheduler:
	if [ "$(LATIGO_PRODUCTION_BRANCH)" == "$(CIRCLE_BRANCH)" ]; then\
		docker build . -f Dockerfile.scheduler -t "${LATIGO_SCHEDULER_IMAGE_NAME}" -t "${LATIGO_SCHEDULER_IMAGE_RELEASE_NAME}";\
	elif [ "$(LATIGO_STAGE_BRANCH)" == "$(CIRCLE_BRANCH)" ]; then\
		docker build . -f Dockerfile.scheduler -t "${LATIGO_SCHEDULER_IMAGE_NAME}" -t "${LATIGO_SCHEDULER_IMAGE_STAGE_NAME}" -t "${LATIGO_SCHEDULER_IMAGE_NAME}:tag${CIRCLE_TAG}";\
	else\
		export TAG_NAME="UNKNOWN BRANCH";\
	fi;\

build-executor:
	if [ "$(LATIGO_PRODUCTION_BRANCH)" == "$(CIRCLE_BRANCH)" ]; then\
		docker build . -f Dockerfile.executor -t "${LATIGO_EXECUTOR_IMAGE_NAME}" -t "${LATIGO_EXECUTOR_IMAGE_RELEASE_NAME}";\
	elif [ "$(LATIGO_STAGE_BRANCH)" == "$(CIRCLE_BRANCH)" ]; then\
		docker build . -f Dockerfile.executor -t "${LATIGO_EXECUTOR_IMAGE_NAME}" -t "${LATIGO_EXECUTOR_IMAGE_STAGE_NAME}" -t "${LATIGO_EXECUTOR_IMAGE_NAME}:tag${CIRCLE_TAG}";\
	else\
		export TAG_NAME="UNKNOWN BRANCH";\
	fi;\

build-images: build-scheduler build-executor


############### Push docker images ####################

push-scheduler: build-scheduler
	export DOCKER_NAME=${LATIGO_SCHEDULER_IMAGE_NAME};\
	export DOCKER_IMAGE=${LATIGO_SCHEDULER_IMAGE_NAME};\
	bash deploy/docker_push.sh

push-executor: build-executor
	export DOCKER_NAME=${LATIGO_EXECUTOR_IMAGE_NAME};\
	export DOCKER_IMAGE=${LATIGO_EXECUTOR_IMAGE_NAME};\
	bash deploy/docker_push.sh

push-images: push-scheduler push-executor

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
	@echo " Gordo targets:"
	@echo ""
	@echo " + login-gordo           Login to gordo cluster"
	@echo " + list-gordos           List available projects in gordo"
	@echo " + port-forward          Set up port forwarding to access gordo via localhost:8888"
	@echo ""
	@echo " Development targets:"
	@echo ""
	@echo " + make help             Show this help"
	@echo " + make up               Build incrementally, test and run all from scratch"
	@echo " + make down             Shutdown docker images"
	@echo " + make influxdb         Rebuild and restart influx image separately, attaching to log"
	@echo " + make grafana          Rebuild and restart grafana image separately, attaching to log"
	@echo " + make postgres         Rebuild and restart postgres image separately, attaching to log"
	@echo " + make adminer          Rebuild and restart adminer image separately, attaching to log"
	@echo " + make scheduler        Rebuild and restart scheduler image separately, attaching to log"
	@echo " + make executor         Rebuild and restart executor images separately, attaching executor-1 to log"
	@echo ""
	@echo " Deployment targets:"
	@echo ""
	@echo " + make build-scheduler  Build scheduler docker image"
	@echo " + make build-executor   Build executor docker image"
	@echo " + make build-images     Build all docker images"
	@echo " + make push-scheduler   Build and push scheduler docker image"
	@echo " + make push-executor    Build and push executor docker image"
	@echo " + make push-images      Build and push all docker images"
	@echo ""

