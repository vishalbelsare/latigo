# latigo
IOC client for the Gordo Machine Learning system.

## Program architecture

The application operates through the use of the following interfaces:

### SensorInformationProvider

Where can we get information about available sensors and their naming conventions?

Possible implementations:

- Tilstandomatic
- Data api

Suggested interface:

- get_sensor_list() – enumerate all available sensors
- sensor_exists(sensor_name:string) – check if a sensor exists

### SensorDataProvider

Where can we get access to data from a sensor given its name?

Possible implementations:

- InfluxDB
- Data api

Suggested interface:

- get_native_range_specifier(from:timestamp, to:timestamp, parameters:string) – return a specification of the given time span in native representation. For example for influx this would be an influx query or complete query url (parameter can be used to select)
- get_data_for_range(from:timestamp, to:timestamp)

### ModelInformationProvider

Where can we get information about available models?

Possible implementations:

- Tilstandomatic

Suggested interface:

- get_model_list() – enumerate all available models
- model_exists(model_name:string) – check if a model exists

### ModelExecutionProvider

Where can we train and execute models?

Possible implementations:

- Gordo

Suggested interface:

- register_model(model_data:json) – Register a new model into the execution provider
- unregister_model(model_ name:string) – Unregister existing model from execution provider
- get_model_status(model_name:string) – Return the full status of a model given its name
- execute_model (model_name:string, from:timestamp, to:timestamp) – Train and/or run data through a given model


## Deployment Architecture

- The application is deployable as a docker container.
- The program is implemented in Python 3.7.
- Alchemy is used for accessing databases.
- Database versioning/migration is managed through alembic.
- The python instance is managed by supervisord.


This project is based on the project "ioc-gordo-oracle" ( https://github.com/equinor/ioc-gordo-oracle )


# Getting up with kubernetes

make sure to disable proxy as acess to kubernetes goes via external network

az login
az aks install-cli
az aks get-credentials --overwrite-existing --resource-group gordotest28 --name gordotest28 --admin


kubectl config set-context --current --namespace=kubeflow
kubectl get gordos

