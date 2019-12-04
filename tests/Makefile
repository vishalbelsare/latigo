ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
.PHONY: h all all devops unit integration load help

h: help

all: unit integration load

devops: test-unit

unit:
	py.test -vv unit

utils:
	py.test -vv unit/test_utils.py

rfc3339:
	py.test -vv unit/test_rfc3339.py

clock:
	py.test -vv unit/test_clock.py

executor:
	py.test -vv unit/test_executor.py

integration:
	py.test -vv integration

load:
	py.test -vv load

gordo:
	py.test -vv unit/test_gordo_client.py
	py.test -vv integration/test_gordo_client.py

time_series:
	py.test -vv unit/test_time_series_api.py
	py.test -vv integration/test_time_series_api.py

event_hub:
#	py.test -vv unit/test_event_hub.py
	py.test -vv integration/test_event_hub.py
	


############### Help ####################

help:
	@echo "#############################################"
	@echo "# This is a conveneince Makefile for Latigo #"
	@echo "#############################################"
	@echo ""
	@echo " Available targets:"
	@echo ""
	@echo " + make help          Show this help"
	@echo " + make all           Run all tests"
	@echo " + make devops        Run devops tests"
	@echo ""
	@echo " + make unit          Run unit tests"
	@echo " + make utils         Run unit tests for utils"
	@echo " + make rfc3339       Run unit tests for rfc3339"
	@echo " + make clock         Run unit tests for clock"
	@echo " + make executor      Run unit tests for executor"
	@echo ""
	@echo " + make integration   Run integration tests"
	@echo " + make gordo         Run gordo integration tests"
	@echo " + make time_series   Run time series API integration tests"
	@echo " + make event_hub     Run event hub integration tests"
	@echo ""
	@echo " + make load          Run load tests"
	@echo ""
