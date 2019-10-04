all: code-quality test-all

flake:
	flake8 --ignore=E731,W503,W504,E501,E265,C0301,W1202,W1203 --max-complexity 10 --exclude build,junk --exit-zero ../

pylint:
	pylint --exit-zero --rcfile pylintrc ../app

mypy:
	mypy --ignore-missing-imports ../app  || true

coverage:
	python -m pytest --junitxml=junit-results.xml --cov=. --cov-report=xml --cov-report=html unit

code-quality: flake pylint mypy

test-devops: test-unit

test-all: test-unit test-integration test-load

test-integration:
	py.test integration

test-unit:
	py.test unit

test-integration:
	py.test integration

test-load:
	py.test load

low-hanging:
	flake8 --select=F401 --max-complexity 10 --exclude build,junk --exit-zero ../
	flake8 --select=F403 --max-complexity 10 --exclude build,junk --exit-zero ../
	flake8 --select=F821 --max-complexity 10 --exclude build,junk --exit-zero ../
	flake8 --select=F841 --max-complexity 10 --exclude build,junk --exit-zero ../
	flake8 --select=W0107 --max-complexity 10 --exclude build,junk --exit-zero ../
	flake8 --select=W0706 --max-complexity 10 --exclude build,junk --exit-zero ../
	flake8 --select=W0105 --max-complexity 10 --exclude build,junk --exit-zero ../
