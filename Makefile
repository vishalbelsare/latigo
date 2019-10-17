ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
APP_DIR:="${ROOT_DIR}/app"
TESTS_DIR:="${ROOT_DIR}/tests"
CODE_QUALITY_DIR:="${ROOT_DIR}/code_quality"
SHELL := /bin/bash
COMPUTED_ENV="${ROOT_DIR}/set_env.py"
.PHONY: all code-quality tests set-env postgres-permission setup up rebuild-req

all: up

code-quality:
	cd "${CODE_QUALITY_DIR}" && make

tests:
	cd "${TESTS_DIR}" && make

show-env:
	env | grep -i latigo

postgres-permission:
	sudo mkdir "${ROOT_DIR}/volumes/postgres" -p && sudo chown -R lroll:lroll "${ROOT_DIR}/volumes/postgres"

rebuild-req:
	pip install --upgrade pip
	pip uninstall gordo-components -y
	pip install --upgrade pip-tools
	cd app && cat requirements.in | sort -u > r.in
	cd app && pip-compile --output-file=requirements.txt r.in
	cd app && cat requirements.in, test_requirements.in | sort -u > r.in
	cd app && pip-compile --output-file=test_requirements.txt r.in

# Rebuild latest latigo and install it to site-packages
setup:
	rm -rf app/build
	pip uninstall -y latigo
	pip install app/

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

scheduler:
	docker-compose up --build -d latigo-scheduler
	docker-compose logs -f latigo-scheduler

executor-1:
	docker-compose up --build -d latigo-executor-1
	docker-compose logs -f latigo-executor-1

executor-2:
	docker-compose up --build -d latigo-executor-2
	docker-compose logs -f latigo-executor-2
