ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
.PHONY: h all all devops unit integration load help

h: help

all: unit integration load

devops: test-unit

unit:
	py.test -vv unit

integration:
	py.test -vv integration

load:
	py.test -vv load

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
	@echo " + make unit          Run unit tests"
	@echo " + make integration   Run integration tests"
	@echo " + make load          Run load tests"
	@echo ""
