# Latigo - Continuous Prediction Service

## About

Latigo is a service that is responsible for continuously running machine learning algorithms on a set of input sensor data to predict the next datapoint in sensor data. This is useful to do predictive maintenance for production equipment.

The basic operation follows these steps:
- Follow a predefined schedule to determine when prediction should occur.
- Fetches meta data about which data sources and ML models to use from [Gordo](/equinor/gordo-components).
- Fetches the source sensor data from the timeseries API.
- Uses Gordo to generate the predictions.
- Persists the resulting predictions back to the timeseries API.

This project has been based on the original prototype project [ioc-gordo-oracle] ( /equinor/ioc-gordo-oracle ) and has since evolved to support other needs and technical dependencies.

## Architecture

### Nodes
Latigo is a distributed application with two nodes:

- Scheduler
- Executor

While Latigo is made to be portable and reusable for other clients, we are coarsly following the needs of IOC right now since that is where it will be used first. IOC has the following requirement:

- Produce a prediction for the last 30 minutes for every ML model in Gordo (there are roughly 9000 models)
- Backfill predictions up to a certain amount of time for every ML model in Gordo so that historical prediction can be reviewed (one-time operation at startup)


#### Scheduler

The scheduler will produce one "task description" for each prediction to be made. The task description will contain the following:
- Timespan for prediction
- The sensor_data tags to predict for
- The Gordo config for the prediction (which "Gordo machine" to use)

The scheduler will produce these tasks according to the schedule and feed them into an event hub.

#### Executor

The executors will then pick tasks from the event_hub and "execute" them one by one.There may be more one executor operating concurrently.

For each tasks the executors will do as follows:
- Read one tasks description
- Find and download the data required for the prediction
- Send the data to Gordo and produce a prediction
- Download the prediction result from Gordo
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


### Dependencies

- The application is deployable as *docker* containers with *docker-compose*.
- The *scheduler* and *executor* programs are implemented in *Python 3.7*.
- *PostgreSQL* is the database used
- *Alchemy* is used as the ORM.
- Database versioning/migration is managed through *alembic*.
- The python instance is managed by *supervisord*.


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

Ensure that a new file called "local_config.yaml" was created.

IMPORTANT: You must open this file and fill in the correct values. Some of the settings you need will be explained in the next sections, but you must ensure all are set up OK.

### Set up event hub

Go to Azure portal and create a event_hubs namespace that has **Kafka enabled** (important).
Create a new event_hub in the namespace for testing and copy the connection string for your event_hub to clipboard. See screenshot for example:

![Event Hub Connection string](documentation/screenshots/event_hub_connection_string.png?raw=true "Event Hub Connection string")

### Put event hub connection string into local config

Open "local_config.yaml" in your favorite editor and make sure to paste your event hub connection string for the key "LATIGO_INTERNAL_EVENT_HUB"

### Set up environment from local_config

Once your local_config is set up correctly, you can use the following steps to produce an environment from that file.

```bash
# See that your changes in config are reflected in output
./set_env.py

# Evaluate output to actually set the environment variables
eval $(./set_env.py)

# see that environment was actually set
env | grep LATIGO
```


Now your environment is set up and docker-compose will pass this environment on to the nodes to let them function correctly

### Start docker compose

You can use docker-compose directly or you can use the [Makefile](#makefile). Please keep in mind that the Makefile is a convenience wrapper and will be explained after the docker-compose basics have been covered.

```bash
# Start the services
docker-compose up
```

At this point you should see the services running:

- influxdb
- adminer
- postgres
- grafana
- latigo-executor-2
- latigo-scheduler
- latigo-executor-1


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

There is a makefile in the project that is meant as a convenience to save time, and also as a reference for commands. To see the commands, simply open it in a text editor. The Makefile is selfdocumenting, to see what it contains, simply invoke it without a target like so:

```bash
make
```

## Connecting directly to Gordo

### About Gordo
Gordo is the actual prediction engine that Latigo will lean on to get work done. Gordo is a kubernetes cluster, and you will need access to this cluster for Latigo to be usefull.

There are some things you need to know about Gordo up front:

- Gordo is in active development
- At the time of writing (2019-10-17) there currently exists no Gordo in "production", however many candidate clusters are running. You will have to communicate with Gordo team to find out which of their test/dev clusters are the best to be using while testing. Some are more stable than others.
- If you need to access Gordo directly during development for debugging purposes you can use port forwarding. This is documented below.
- Latigo will connect to Gordo using api gateway and a so called "bearer token" for authentication.

### Disable proxy
Before you can have portforwarding set up successfully, you need to disable proxy settings (Gordo is available via external network). For more information about proxy setup in Equinor please see [this link](https://wiki.equinor.com/wiki/index.php/ITSUPPORT:Linux_desktop_in_Statoil#Proxy_settings).

```bash
# Disable proxy
unsetproxy
```

### Log in to azure

```bash
az login
```
*NOTE: At this point you should see a list of subscriptions that you have access to in the terminal. Make sure you see the subscription(s) you expect to be working with!*

### Select active subscription
```bash
# To see the list of available subscriptions you can use the command:
az account list

# Now select active subscription.
az account set --subscription "019958ea-fe2c-4e14-bbd9-0d2db8ed7cfc"

# Make sure the correct one is set
az account show
```
*NOTE: We used "Data Science POC - Non production" in this example which is the correct one to use at the time of writing (2019-10-21).*

### Install azure AKS tools
```bash
# If you don't have aks tools such as kubectl and other commands, install it like this:
az aks install-cli
```
*NOTE: You only need to do this once*


### Select cluster
```bash
# Now we can tell aks to focus on one particular cluster
az aks get-credentials --overwrite-existing --resource-group gordotest28 --name gordotest28 --admin
```
*NOTE: Here we used "gordotest28" as a placeholder for the actual cluster name that you will use. Please ask Gordo team which cluster that is recommende for use*

### Select context
Now that we have selected which cluster to work with we can start sending commands to it with kubectl
```bash
# Set the kubernetes context with namespace
kubectl config set-context --current --namespace=kubeflow
```

### List Gordo projects
```bash
# Now we can list all the "Gordo projects" running in this cluster
kubectl get gordos
```

### Set up port forwarding to Gordo cluster
```bash
# Now we set up port forwarding so that our code can talk to the cluster
kubectl port-forward svc/ambassador -n ambassador 8080:80
```
*NOTE: Here 8080 is the port you want to use locally. Feel free to use whatever port is convenient for you.*
To terminate the port forwarding simply stop the process with <ctrl>+<C>.

*NOTE: The port forwarding can be flaky and will likely quit at random. To overcome the frustration, you can use the command below:*
```bash
# Put portforwarding in infinite loop so it is restarted whenever it go down unexpectedly
make port-forward
```

*To verify that the connection works, you could open the URL for a Gordo project in the browser:*
```bash
xdg-open http://localhost:8080/gordo/v0/ioc-1130/
```
*NOTE: Please make sure to use correct port and project name. We used "8080" and "ioc-1130" as placeholders in the example.*

🍰 Now you should see a browser full of metadata in json format signaling that you are now ready to connect to cluster from code!

## Requirement pinning

We use requirements.in and requirements.txt files to keep track of dependencies. requirements.in is the version ranges we want. We use make file to convert this into requirements.txt which are the exactly pinned requirements.

```bash
# Rebuild requirements.txt from requirements.in
make rebuild-req
```

NOTE: Both requirements.in and requirements.txt are kept in git
