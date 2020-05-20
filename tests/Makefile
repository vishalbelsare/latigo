ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
.PHONY: h all all devops unit integration load help

h: help

all: utils scheduler executor

devops: unit

unit:
	# TODO refactor and add here all unit test
	py.test -vv unit/test_utils.py unit/test_executor.py unit/test_scheduler.py

utils:
	py.test -vv unit/test_utils.py

rfc3339:
	py.test -vv unit/test_rfc3339.py

clock:
	py.test -vv unit/test_clock.py

executor:
	py.test -vv unit/test_executor.py

scheduler:
	py.test -vv unit/test_scheduler.py

integration:
	py.test -vv integration

integration_metadata_api:
	py.test -vv integration/metadata_api

load:
	py.test -vv load

gordo: u_gordo i_gordo 

time_series: u_time_series i_time_series

event_hub: u_event_hub i_event_hub

intermediate:
	py.test -vv unit/test_intermediate.py

u_gordo:
	py.test -vv unit/test_gordo_client.py

u_time_series:
	py.test -vv unit/test_time_series_api.py

u_event_hub:
	py.test -vv unit/test_event_hub.py

i_gordo:
	py.test -vv integration/test_gordo_client.py

i_time_series:
	py.test -vv integration/test_time_series_api.py

i_event_hub:
	py.test -vv integration/test_event_hub.py

i_auth:
	py.test -vv integration/test_auth.py


############### Help ####################

help:
	@echo "#############################################"
	@echo "# This is a conveneince Makefile for Latigo #"
	@echo "#############################################"
	@echo ""
	@echo " General targets:"
	@echo ""
	@echo " + make help            Show this help"
	@echo " + make all             Run all tests"
	@echo " + make devops          Run devops tests"
	@echo " + make load            Run load tests (WIP)"
	@echo ""
	@echo "Unit targets:"
	@echo ""
	@echo " + make unit            Run unit tests"
	@echo " + make utils           Run unit tests for utils"
	@echo " + make rfc3339         Run unit tests for rfc3339"
	@echo " + make clock           Run unit tests for clock"
	@echo " + make executor        Run unit tests for executor"
	@echo " + make intermediate    Run unit tests for data converter"
	@echo " + make u_gordo         Run gordo unit tests"
	@echo " + make u_time_series   Run time series API unit tests"
	@echo " + make u_event_hub     Run event hub unit tests"
	@echo ""
	@echo "Integration targets:"
	@echo ""
	@echo " + make integration     Run integration tests"
	@echo " + make i_gordo         Run gordo integration tests"
	@echo " + make i_time_series   Run time series API integration tests"
	@echo " + make i_event_hub     Run event hub integration tests"
	@echo " + make i_auth          Run auth integration tests"
	@echo ""
	@echo "Component targets:"
	@echo ""
	@echo " + make u_gordo         Run all gordo tests"
	@echo " + make u_time_series   Run all time series API tests"
	@echo " + make u_event_hub     Run all event hub tests"
	@echo " + make load            Run load tests"
	@echo ""
