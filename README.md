# Latigo - Continuous Prediction Service

## About

Latigo is a service that follows a schedule to feed Gordo with prediction tasks and data and stores the result.

This project was based on the original prototype project "ioc-gordo-oracle" ( https://github.com/equinor/ioc-gordo-oracle ) and has since evolved to support other needs and technical dependencies.

## Architecture

### Nodes
Latigo is a distributed application with two nodes:

- Scheduler
- Executor

While Latigo is made to be portable and reusable for other clients, we are coarsly following the needs of IOC right now since that is where it will be used first. IOC has the following requirement:

- Produce a prediction for the last 30 minutes for every ML model in gordo (there are roughly 9000 models)
- Backfill predictions up to a certain amount of time for every ML model in gordo so that historical prediction can be reviewed (one-time operation at startup)

The scheduler will produce one "task description" for each prediction to be made. The task description will contain the following:
- Timespan for prediction
- The sensor_data tags to predict for
- The gordo config for the prediction ("machine" to use (combination of model and parameters))

The scheduler will produce these tasks according to the schedule and feed them into an event hub.

The executors will then pick tasks from the event_hub and "execute" them one by one.There may be more one executor operating concurrently.

For each tasks the executors will do as follows:
- Read one tasks description
- Find and download the data required for the prediction
- Send the data to gordo and produce a prediction
- Download the prediction result from gordo
- Find and upload the prediction result to the data sink that is supposed to store the result.


### Interfaces

Latigo opperates through the use of the following interfaces:

- SensorInformationProvider
- SensorDataProvider
- ModelInformationProvider
- ModelExecutionProvider

#### SensorInformationProvider

Where can we get information about available sensors and their naming conventions?

Possible implementations:

- Tilstandomatic
- Data api

Suggested interface:

- get_sensor_list() – enumerate all available sensors
- sensor_exists(sensor_name:string) – check if a sensor exists

#### SensorDataProvider

Where can we get access to data from a sensor given its name?

Possible implementations:

- InfluxDB
- Data api

Suggested interface:

- get_native_range_specifier(from:timestamp, to:timestamp, parameters:string) – return a specification of the given time span in native representation. For example for influx this would be an influx query or complete query url (parameter can be used to select)
- get_data_for_range(from:timestamp, to:timestamp)

#### ModelInformationProvider

Where can we get information about available models?

Possible implementations:

- Tilstandomatic

Suggested interface:

- get_model_list() – enumerate all available models
- model_exists(model_name:string) – check if a model exists

#### ModelExecutionProvider

Where can we train and execute models?

Possible implementations:

- Gordo

Suggested interface:

- register_model(model_data:json) – Register a new model into the execution provider
- unregister_model(model_ name:string) – Unregister existing model from execution provider
- get_model_status(model_name:string) – Return the full status of a model given its name
- execute_model (model_name:string, from:timestamp, to:timestamp) – Train and/or run data through a given model


### Deployment

- The application is deployable as a docker container.
- The program is implemented in Python 3.7.
- Alchemy is used for accessing databases.
- Database versioning/migration is managed through alembic.
- The python instance is managed by supervisord.


# Development

## Prequisites

- Git with authentication set up (https://wiki.equinor.com/wiki/index.php/Software:Git_Tutorial_Getting_Setup)
- Python 3.x
- Docker and docker-compose installed (https://wiki.equinor.com/wiki/index.php/WIKIHOW:Set_up_Docker_on_a_CentOS_7_server)
- Connection string to Azure Event Hub and both read/write permission to it (documentation on how to obtrain this follows)

## Steps

### Clone project and enter project folder
```bash

cd <where you keep your projects>

clone git@github.com:equinor/latigo.git

cd latigo
```
### Create local configuration file
```bash
# Create local config if it does not exist
./set_env.py

# See that it is created
ls -halt | grep local
```

Ensure that a new file called "local_config.yaml" was created

### Set up event hub

Go to Azure portal and copy the connection string for your eventhub to clipboard. See screenshot for example

![Event Hub Connection string](documentation/screenshots/event_hub_connection_string.png?raw=true "Event Hub Connection string")

### Put event hub connection string into local config

Open "local_config.yaml" in your favorite editor and make sure to paste your event hub connection string for the key "LATIGO_INTERNAL_EVENT_HUB"

### Set up environment from local_config

```bash
# See that your changes in config are reflected in output
./set_env.py

# Evaluate output to actually set the environment variables
eval $(./set_env.py)

# see that environment was actually set
env | grep LATIGO
```

Now your environment is set up and docker-compose will use it to connect to correct event hub

### Start docker compose

You can use docker-compoes directly or you can use the Makefile. The makefile is just a convenience wrapper and will be explained after the docker-compose basics have been covered.

```bash
# Start the services
docker-compose up
```

At this point you should see 3 services running:
- scheduler
- executor 1
- executor 2

### Rebuilding services

During development you might want to rebuild only one service. To accomplish this you can do the following:

- Open a new terminal window / tab
- Navigate to project folder
- Restart named service with the --build switch

```bash
# Rebuild and restart one service of already running docker compose setup:
docker-compose up --build latigo-scheduler

```

You can also "detach" one service and view it's log independently of the other services like this:

```bash
# Rebuild and restart one service in DETACHED state
docker-compose up --detach --build latigo-scheduler

# follow log of that service only
docker-compose logs --follow latigo-scheduler

# Please note that stopping the last will NOT stop the service, simply "unhook" the log output.
```

### Makefile

The Makefile is there mainsly as a convenience. It is recommended to see what id does for you simply by opening it in a text editor.

This section highlights some features.


```bash


# Run code quality tools
make code-quality

# Run all tests
make tests

# Show the variables related to latigo in the current environment
make show-env

# Set up permissions of the postgres docker image's volume (necessary nuisance)
make postgres-permission

# Rebuild pinned versions in requirements.txt and test_requirements.txt from requirements.in and test_requirements.in respectively
make rebuild-req

# Build latigo pip package
make setup

# Build docker images
make build

# Build incrementally, test and run all from scratch (this is default action when you don't specify a target to the make command)
make up

# Shutdown docker images
make down

# Rebuild and restart influx image separately, attaching to log
make influxdb

# Rebuild and restart grafana image separately, attaching to log
make influxdb

# Rebuild and restart postgres image separately, attaching to log
make influxdb

# Rebuild and restart adminer image separately, attaching to log
make influxdb

# Rebuild and restart scheduler image separately, attaching to log
make influxdb

# Rebuild and restart executor-1 image separately, attaching to log
make influxdb

# Rebuild and restart executor-2 image separately, attaching to log
make influxdb
```


# Getting up with kubernetes

make sure to disable proxy as access to kubernetes goes via external network

az login
az aks install-cli
az aks get-credentials --overwrite-existing --resource-group gordotest28 --name gordotest28 --admin


kubectl config set-context --current --namespace=kubeflow
kubectl get gordos

## Requirement pinning

We use requirements.in and requirements.txt files to keep track of dependencies. requirements.in is the version ranges we want. We use make file to convert this into requirements.txt which are the exactly pinned requirements.

```bash
# Rebuild requirements.txt from requirements.in
make rebuild-req
```

NOTE: Both requirements.in and requirements.txt are kept in git


