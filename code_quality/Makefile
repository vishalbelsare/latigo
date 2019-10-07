ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
APP_DIR="${ROOT_DIR}/../app"

.PHONY: all flake pylint mypy coverage black low-hanging

all: black flake mypy #pylint is broken, disabled for now

flake:
	flake8 --ignore=E731,W503,W504,E501,E265,C0301,W1202,W1203 --max-complexity 10 --exclude build,junk --exit-zero "${ROOT_DIR}/app"

pylint:
	pylint --exit-zero --rcfile pylintrc --output-format=colorized "${APP_DIR}"

mypy:
	mypy --ignore-missing-imports "${APP_DIR}"

coverage:
	python -m pytest --junitxml=junit-results.xml --cov="${APP_DIR}" --cov-report=xml --cov-report=html unit

black:
	black -l 999 -t py37 "${APP_DIR}"

#	autopep8 -r -i -j 0 --max-line-length 999 -a -a -a ./

low-hanging:
	flake8 --select=F401 --max-complexity 10 --exclude build,junk --exit-zero "${APP_DIR}"
	flake8 --select=F403 --max-complexity 10 --exclude build,junk --exit-zero "${APP_DIR}"
	flake8 --select=F821 --max-complexity 10 --exclude build,junk --exit-zero "${APP_DIR}"
	flake8 --select=F841 --max-complexity 10 --exclude build,junk --exit-zero "${APP_DIR}"
	flake8 --select=W0107 --max-complexity 10 --exclude build,junk --exit-zero "${APP_DIR}"
	flake8 --select=W0706 --max-complexity 10 --exclude build,junk --exit-zero "${APP_DIR}"
	flake8 --select=W0105 --max-complexity 10 --exclude build,junk --exit-zero "${APP_DIR}"

