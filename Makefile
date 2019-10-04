all: up

pepify:
	autopep8 -r -i -j 0 --max-line-length 999 -a -a -a ./

test-all:
	cd tests && make

set-env:
	./set_env.py
	eval $(./set_env.py)
	env | grep -i latigo

postgres-permission:
	sudo chown -R lroll:lroll volumes/postgres

# Rebuild latest latigo and install it to site-packages before starting tests
setup:
	rm -rf app/build
	pip uninstall -y latigo
	pip install app/

up: set-env postgres-permission pepify setup test-all
	docker-compose up --build


rebuild-req:
	pip uninstall gordo-components -y
	pip install --upgrade pip-tools
	cd app && cat requirements.in | sort -u > r.in
	cd app && pip-compile --output-file=requirements.txt r.in
	cd app && cat requirements.in, test_requirements.in | sort -u > r.in
	cd app && pip-compile --output-file=test_requirements.txt r.in
