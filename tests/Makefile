
test-unit: install-pip
	py.test unit

# Rebuild latest latigo and install it to site-packages before starting tests
install-pip:
	pip uninstall -y latigo
	../app/setup.py build
	pip install ../app

test-integration:
	py.test integration

flake:
	flake8 --ignore=E731,W503,W504,E501 --max-complexity 10 --exit-zero ../

pylint:
	pylint --exit-zero --rcfile .pylintrc ../app

typing:
	mypy --ignore-missing-imports .. ../app

coverage:
	python -m pytest --junitxml=junit-results.xml --cov=. --cov-report=xml --cov-report=html unit

code-quality: flake pylint typing

test-all: test-unit test-integration

test-devops: test-unit coverage
