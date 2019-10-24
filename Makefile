ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
APP_DIR:="${ROOT_DIR}/app"
TESTS_DIR:="${ROOT_DIR}/tests"
CODE_QUALITY_DIR:="${ROOT_DIR}/code_quality"
SHELL := /bin/bash
COMPUTED_ENV="${ROOT_DIR}/set_env.py"
.PHONY: all code-quality tests set-env postgres-permission setup up rebuild-req

all: help

code-quality:
	cd "${CODE_QUALITY_DIR}" && make

tests:
	cd "${TESTS_DIR}" && make

show-env:
	env | grep -i latigo

pgsql-perm :
	sudo mkdir "${ROOT_DIR}/volumes/postgres" -p && sudo chown -R lroll:lroll "${ROOT_DIR}/volumes/postgres"

rebuild-req:
	pip install --upgrade pip
	pip uninstall gordo-components -y
	pip install --upgrade pip-tools
	cd app && cat requirements.in | sort -u > r.in
	cd app && pip-compile --output-file=requirements.txt r.in
	cd app && cat requirements.in, test_requirements.in | sort -u > r.in
	cd app && pip-compile --output-file=test_requirements.txt r.in
	[ -f r.in ] && rm r.in

# Rebuild latest latigo and install it to site-packages
setup:
	rm -rf app/build
	pip uninstall -y latigo
	pip install app/

port-forward:
	while : ; do printf "PORTFORWARDING----\n"; kubectl port-forward svc/ambassador -n ambassador 8888:80; done


build: postgres-permission setup code-quality tests show-env
	docker-compose build

up: build
	# NOTE: The volumes folder must not be inside the context of any docker or the docker builds will fail!
	sudo mkdir -p ../volumes/latigo/influxdb/data
	sudo mkdir -p ../volumes/latigo/grafana/data
	sudo chown 472:472 ../volumes/latigo/grafana/data
	docker-compose up
	docker ps -a

down:
	docker-compose down
	docker ps -a

influxdb:
	docker-compose up --build -d influxdb
	docker-compose logs -f influxdb

grafana:
	docker-compose up --build -d grafana
	docker-compose logs -f grafana

postgres:
	docker-compose up --build -d postgres
	docker-compose logs -f postgres

adminer:
	docker-compose up --build -d adminer
	docker-compose logs -f adminer

scheduler: build
	docker-compose up --build -d latigo-scheduler
	docker-compose logs -f latigo-scheduler

executor-1: build
	docker-compose up --build -d latigo-executor-1
	docker-compose logs -f latigo-executor-1

executor-2: build
	docker-compose up --build -d latigo-executor-2
	docker-compose logs -f latigo-executor-2


help:
	@echo "#############################################"
	@echo "# This is a conveneince Makefile for Latigo #"
	@echo "#############################################"
	@echo ""
	@echo " Available targets:"
	@echo ""
	@echo " + make help          Show this help"
	@echo " + make up            Build incrementally, test and run all from scratch"
	@echo " + make down          Shutdown docker images"
	@echo " + make influxdb      Rebuild and restart influx image separately, attaching to log"
	@echo " + make grafana       Rebuild and restart grafana image separately, attaching to log"
	@echo " + make postgres      Rebuild and restart postgres image separately, attaching to log"
	@echo " + make adminer       Rebuild and restart adminer image separately, attaching to log"
	@echo " + make scheduler     Rebuild and restart scheduler image separately, attaching to log"
	@echo " + make executor-1    Rebuild and restart executor-1 image separately, attaching to log"
	@echo " + make executor-2    Rebuild and restart executor-2 image separately, attaching to log"
	@echo ""
	@echo " + make code-quality  Run code quality tools"
	@echo " + make tests         Run (almost) all tests. NOTE: For more options see tests/Makefile"
	@echo " + make show-env      Show the variables related to Latigo in the current environment"
	@echo " + make pgsql-perm    Set up permissions of the postgres docker image's volume (necessary nuisance)"
	@echo " + make rebuild-req   Rebuild pinned versions in *requirements.txt from *requirements.in"
	@echo " + make setup         Build latigo pip package"
	@echo " + make build         Build docker images"
	@echo ""
