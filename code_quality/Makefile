ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
APP_DIR="${ROOT_DIR}/../app"
TESTS_DIR="${ROOT_DIR}/../tests"


.PHONY: h all flake pylint mypy coverage black low-hanging help

h: help

all: black flake mypy #pylint is broken, disabled for now

flake:
	flake8 --ignore=E731,W503,W504,E501,E265,C0301,W1202,W1203 --max-complexity 10 --exclude build,junk --exit-zero "${ROOT_DIR}/app"

pylint:
	pylint --exit-zero --rcfile pylintrc --output-format=colorized "${APP_DIR}"
	pylint --exit-zero --rcfile pylintrc --output-format=colorized "${TESTS_DIR}"

mypy:
	# mypy is sometimes too sensitive so we allow failure
	mypy --ignore-missing-imports "${APP_DIR}" || true
	mypy --ignore-missing-imports "${TESTS_DIR}"  || true

black:
	black -l 120 -t py37 "${APP_DIR}"
	black -l 120 -t py37 "${TESTS_DIR}"

coverage:
	python -m pytest --junitxml=junit-results.xml --cov="${APP_DIR}" --cov-report=xml --cov-report=html unit

#	autopep8 -r -i -j 0 --max-line-length 999 -a -a -a ./

############### Help ####################

help:
	@echo "#############################################"
	@echo "# This is a conveneince Makefile for Latigo #"
	@echo "#############################################"
	@echo ""
	@echo " Available targets:"
	@echo ""
	@echo " + make help          Show this help"
	@echo " + make all           Run all targets"
	@echo " + make flake         Run flake"
	@echo " + make mypy          Run mypy"
	@echo " + make pylint        Run pylint"
	@echo " + make coverage      Run coverage"
	@echo " + make black         Run black"
	@echo ""
