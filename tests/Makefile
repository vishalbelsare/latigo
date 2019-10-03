all: install-pip code-quality test-all


# Rebuild latest latigo and install it to site-packages before starting tests
install-pip:
	pip uninstall -y latigo
	../app/setup.py build
	pip install ../app

test-integration:
	py.test integration

flake:
	flake8 --ignore=E731,W503,W504,E501 --max-complexity 10 --exclude build,junk --exit-zero ../

pylint:
	pylint --exit-zero --rcfile pylintrc ../app

typing:
	mypy --ignore-missing-imports .. ../app

coverage:
	python -m pytest --junitxml=junit-results.xml --cov=. --cov-report=xml --cov-report=html unit

code-quality: flake pylint typing coverage

test-all: test-unit test-integration

test-devops: test-unit coverage

test-unit: install-pip
	py.test unit

pepify:
	autopep8 -r -i -j 0 -a -a -a ../

low-hanging:
	flake8 --select=F401 --max-complexity 10 --exclude build,junk --exit-zero ../
	flake8 --select=F403 --max-complexity 10 --exclude build,junk --exit-zero ../
	flake8 --select=F821 --max-complexity 10 --exclude build,junk --exit-zero ../
	flake8 --select=F841 --max-complexity 10 --exclude build,junk --exit-zero ../
	

