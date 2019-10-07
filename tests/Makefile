ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
.PHONY: all test-all test-unit test-integration test-load

all: test-unit

test-devops: test-unit

test-all: test-unit test-integration test-load

test-unit:
	py.test unit

test-integration:
	py.test integration

test-load:
	py.test load
