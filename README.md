# Latigo - Continuous Prediction Service

## Table of content

- [About](#about)
- [License](#license)
- [User manual](#user-manual)
- [Architecture](#architecture)
- [Development](#development)
- [Deployment](#deployment)

## About

Latigo is a service that is responsible for continuously running machine learning algorithms on a set of input sensor data to predict the next datapoint in sensor data. This is useful to do predictive maintenance for industrial equipment.
Latigo is a small part of a larger system developed for Equinor.

The basic operation follows these steps:
- Follow a predefined schedule to determine when prediction should occur.
- Fetches meta data about which data sources and ML models to use from [Gordo](/equinor/gordo-components).
- Fetches the source sensor data from the [Time Series API](/equinor/OmniaPlant/tree/master/Omnia%20Timeseries%20API).
- Uses [Gordo](/equinor/gordo-components) to generate predictions.
- Persists the resulting predictions back to [Time Series API](/equinor/OmniaPlant/tree/master/Omnia%20Timeseries%20API).

This project has been based on the original prototype project [ioc-gordo-oracle](/equinor/ioc-gordo-oracle) and has since evolved to support other needs.

## License

Please see [LICENSE](LICENSE) file for details. Latigo has G-Faps and is licensed under GNU AFFERO GENERAL PUBLIC LICENSE.


## User manual

Once latigo is in production, this section will guide you to how you can manage it.

> NOTE: If you are a developer, maybe you will find the [Architecture](#architecture) and [Development](#development) sections of interest.

> NOTE: If you want to deploy, please see [Deployment](#deployment) section.

Latigo is largely data-driven both in configuration as well as during operations. All parameters of the application can be adjusted via parameters in the configuration. This seciton outlines how you go about changing the parameters and what each parameter means.

### Change parameters

All settings are stored in yaml configuration files. The default values are stored in git:

- [app/deploy/scheduler_config.yaml](app/deploy/scheduler_config.yaml)
- [app/deploy/executor_config.yaml](app/deploy/executor_config.yaml)

During application initialization these values are loaded as the basis of the configuration and then extended in two stages.

#### Extending with yaml config file
First an "overlay" yaml file can be named that will change the default values. To enable this, simply set the environment variable **LATIGO_EXECUTOR_CONFIG_FILE** to pointto a valid yaml config for executor and **LATIGO_SCHEDULER_CONFIG_FILE** respectively.

In production, this is set to use azure vault. Go to azure vault and edit the configurations for *scheduler* and *executor* respectively:
1. **latigo-scheduler-config-yaml**
2. **latigo-executor-config-yaml**

> TIP: You can use make set-secrets to propegate changes to secrets quickly. See the Makefile tagets for how this works.

#### Extending with environment variables

Some settings are overridden by environment variables. You can see which by looking in [app/bin/scheduler.py](app/bin/scheduler.py) and [app/bin/executor.py](app/bin/executor.py) respecively.

For example if you would like to set an alternate base URL for sensor data, simply set **LATIGO_TIME_SERIES_BASE_URL** to the value you want.

In production, this is set to use azure vault.

> NOTE: Environment variables will always override custom yaml config, and custom yaml config will always override default values.

The meaning of each parameter are documented below.

### Available parameter sections

In this section we will give an overview of parameters for latigo scheduler and executor.

> NOTE: There is some overlap, so this has been structured into sections describing parts of the configurations that is referenced later.

#### scheduler

This is the main section for scheduler

| Parameter | Default | Description |
|      ---: | :-----: | :---------- |
| continuous_prediction_start_time | "08:00" | The start time of scheduling. See [scheduling algorithm](#scheduling-algorithm) for details. |
| continuous_prediction_interval | "30m" | The interval of scheduling. See [scheduling algorithm](#scheduling-algorithm) for details. |
| continuous_prediction_delay | "3h" | The prediction delay of scheduling. See [scheduling algorithm](#scheduling-algorithm) for details. |
| projects | ['lat-lit'] | Comma separated list of projects that scheduler will work on. lat-lit is a safe test project for verifying correct operation. |
| back_fill_max_interval | "7d" | How long back to do back-filling. **NOTE: Backfilling is not implemented, this parameter will currently have no effect.** |
| restart_interval_sec | 604800 | An interval by which the program will restart, on opportunity, to clear any built up state. Disabled if set to any value below 1. Set to 7 days for scheduler. |

This is the main section for executor

#### executor
| Parameter | Default | Description |
|      ---: | :-----: | :---------- |
| instance_count | 1 | The number of executor threads to start running in paralell. Should ideally be tweaked so that the app is just barely io/bound, so that kubernetes horizontal autoscaler can be confiured to look at CPU load for automatic scaling. |
| restart_interval_sec | 21600 | An interval by which the program will restart, on opportunity, to clear any built up state. Disabled if set to any value below 1. Set to 6 hours for executor. |

#### task_queue

Both scheduler and executor has a task_queue configuration. It describes their connection to azure event hub via kafka interface that allows scheduler to pushe tasks to executors.

| Parameter | Default | Description |
|      ---: | :-----: | :---------- |
| type | "kafka" | Currently only kafka is supported. There has been "event_hub" and "postgres" in the past. |
| connection_string | not shown | The full connection string as copied from event_hub panel in azure portal. |
| poll_timeout_sec | 100000 | Kafka timeout when waiting for response in client. |
| security.protocol | "SASL_SSL" | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| ssl.ca.location | "/etc/ssl/certs/ca-certificates.crt" | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| sasl.mechanism | "PLAIN" | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| group.id | "1" | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| client.id | "latigo_scheduler" | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| request.timeout.ms | 10000 | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| session.timeout.ms | 10000 | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| default.topic.config | {"auto.offset.reset": "smallest"} | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| debug | "fetch" | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| topic | "latigo_topic" | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| enable.auto.commit | true | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| auto.commit.interval.ms | 1000 | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| max.poll.interval.ms | 86400000 | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |

#### auth

Auth sections are used by gordo and time_series to do oauth2 in azure. They look like this:

| Parameter | Default | Description |
|      ---: | :-----: | :---------- |
| resource | "set from env" | The resource ID in Azure. |
| tenant | "set from env" | The tenant ID in Azure. |
| authority_host_url | "set from env" | The authority host URL in [Azure](https://docs.microsoft.com/en-us/samples/azure-samples/data-lake-analytics-python-auth-options/authenticating-your-python-application-against-azure-active-directory/). |
| client_id | "set from env" | The client ID in Azure. |
| client_secret | "DO NOT PUT SECRETS IN THIS FILE" | The client secret in Azure. |

#### model_info

A source of information about models.

| Parameter | Default | Description |
|      ---: | :-----: | :---------- |
| type | "gordo" | Currently only gordo is supported. |
| connection_string | "DO NOT PUT SECRETS IN THIS FILE" | The connection string by which the program will reach the gordo instance. Parsed and used with gordo client. |
| target | null | Gordo client spesific. See [gordo client documentation](/equinor/gordo/blob/master/gordo/client/client.py). |
| metadata | null | Gordo client spesific. See [gordo client documentation](/equinor/gordo/blob/master/gordo/client/client.py). |
| batch_size | 1000 | Gordo client spesific. See [gordo client documentation](/equinor/gordo/blob/master/gordo/client/client.py). |
| parallelism | 10 | Gordo client spesific. See [gordo client documentation](/equinor/gordo/blob/master/gordo/client/client.py). |
| forward_resampled_sensors | false | Gordo client spesific. See [gordo client documentation](/equinor/gordo/blob/master/gordo/client/client.py). |
| ignore_unhealthy_targets | true | Gordo client spesific. See [gordo client documentation](/equinor/gordo/blob/master/gordo/client/client.py). |
| n_retries | 5 | Gordo client spesific. See [gordo client documentation](/equinor/gordo/blob/master/gordo/client/client.py). |
| use_parquet | true | Gordo client spesific. See [gordo client documentation](/equinor/gordo/blob/master/gordo/client/client.py). |
| data_provider -> debug | true | Gordo client spesific. See [gordo client documentation](/equinor/gordo/blob/master/gordo/client/client.py). |
| data_provider -> n_retries | 5 | Gordo client spesific. See [gordo client documentation](/equinor/gordo/blob/master/gordo/client/client.py). |
| prediction_forwarder -> debug | false | Gordo client spesific. See [gordo client documentation](/equinor/gordo/blob/master/gordo/client/client.py). |
| prediction_forwarder -> n_retries | 5 | Gordo client spesific. See [gordo client documentation](/equinor/gordo/blob/master/gordo/client/client.py). |
| auth | [see the auth section](#auth) | The authentication for accessing gordo |

#### predictor

A service to produce predictions.

> NOTE: This is configured identically to model_info so please see [that section](#model_info).

#### sensor_data

| Parameter | Default | Description |
|      ---: | :-----: | :---------- |
| type | "time_series_api" | The source to use for sensor data. Currently only "time_series_api" is supported. Influx was also relevant at one point. |
| base_url | "https://api.gateway.equinor.com/plant-beta/timeseries/v1.5" | The base URL to use for connecting to time_series_api. See documentation [here](https://api.equinor.com/docs/services/Timeseries-api-v1-5).|
| async | False | Wether or not to use async calls to time_series_api. Currently only False is tested. |
| auth | [see the auth section](#auth) | The authentication for accessing time_series_api. |

#### prediction_storage

| Parameter | Default | Description |
|      ---: | :-----: | :---------- |
| type | "time_series_api" | The sink to use for storing predction data. Currently only "time_series_api" is supported. Influx was also relevant at one point. |
| base_url | "https://api.gateway.equinor.com/plant-beta/timeseries/v1.5" | The base URL to use for connecting to time_series_api. See documentation [here](https://api.equinor.com/docs/services/Timeseries-api-v1-5).|
| async | False | Wether or not to use async calls to time_series_api. Currently only False is tested. |
| auth | [see the auth section](#auth) | The authentication for accessing time_series_api. |

### Scheduling algorithm

The idea is that tasks are scheduled at a predictable clock time, so you know that for example "Every day at 09:30 a new prediction will be performed".

The scheduler operates using the following algorithm:

1. Get the current time of day into **NOW**
2. Get value of **continuous_prediction_start_time** into **X**
3. Add value of **continuous_prediction_interval** to **X** until **X** > **NOW**
4. Set **Y** = **X** - **NOW**
5. Wait until **Y** time passes
6. Queue up tasks for each project in the interval  **continuous_prediction_interval**, going back **continuous_prediction_delay** in time.
7. Repeat

## Architecture

### Nodes
Latigo is a distributed application with two nodes:

- Scheduler
- Executor

While Latigo is made to be portable and reusable for other clients, we are coarsly following the needs of Equinor IOC right now since that is where it will be used first. IOC has the following requirements:

- Produce a prediction for the last 30 minutes for every ML model that is available in Gordo (there are roughly 9000 models at the time of writing).
- Backfill predictions backward to a certain amount of time for every ML model in Gordo so that historical prediction can be reviewed (one-time operation at startup).


#### Scheduler

In Latigo there will be exactly one scheduler instance running. The scheduler instance will produce one "task description" for each prediction to be made. The task description will contain the following:
- Timespan for prediction
- The sensor_data tags to predict for
- The Gordo config for the prediction (which "Gordo machine" to use)

The scheduler will produce these tasks according to the schedule and feed them into an internal message queue ( [Azure Event Hub](https://docs.microsoft.com/en-us/azure/event-hubs/event-hubs-about) ).

#### Executor

In Latigo there will be one or more executor instances running. The executor instances will each pick tasks from the internal message queue and "execute" them one by one.There may be more one executor operating concurrently for scalability.

For each tasks the executors will do as follows:
- Read one tasks description.
- Find the required data for the prediction in the source (Time Series API).
- Download the data required for the prediction from the source (Time Series API).
- Send the data to Gordo and produce prediction results.
- Download the prediction results from Gordo.
- Upload the prediction result to the destination (Time Series API).


### Interfaces

Latigo operates through the use of the following interfaces:

- PredictionExecutionProviderInterface
- PredictionStorageProviderInterface
- SensorDataProviderInterface


#### PredictionExecutionProviderInterface
This interface wraps the engine that produces predictions based on sensor data.
##### Interface
- execute_prediction(project_name: str, model_name: str, sensor_data: SensorData) -> PredictionData

#### PredictionStorageProviderInterface
This interface wraps the destination where predictions are stored.
##### Interface
- put_predictions(prediction_data: PredictionData)

#### SensorDataProviderInterface
This interface wraps the source of sensor data.
##### Interface
- get_data_for_range(spec: SensorDataSpec, time_range: TimeRange) -> SensorData


### Dependencies

- The application is deployable as *docker* containers with *docker-compose*.
- The *scheduler* and *executor* programs are implemented in *Python 3.7*.

## Development

This section will explain how to get up and going with development for Latigo.

### Prequisites
You will need the following:
- Git with authentication set up (see [equinor wiki](https://wiki.equinor.com/wiki/index.php/Software:Git_Tutorial_Getting_Setup))
- Python 3.x
- Docker and docker-compose installed (see [equinor wiki](https://wiki.equinor.com/wiki/index.php/WIKIHOW:Set_up_Docker_on_a_CentOS_7_server))
- Connection string to Azure Event Hub and both read/write permission to it (documentation on how to obtrain this follows)
- Connection string to Time Series API (Possibility of using local influx has been planned but is not complete at this time)

### Steps

#### Clone project and enter project folder
```bash

cd <where you keep your projects>

clone git@github.com:equinor/latigo.git

cd latigo
```
#### Create local configuration file
```bash
# Create local config if it does not exist
./set_env.py

# See that it is created
ls -halt | grep local
```

Ensure that a new file called "local_config.yaml" was created.

> IMPORTANT: You must open this file and fill in the correct values. Some of the settings you need will be explained in the next sections, but you must ensure all are set up OK.

#### Set up event hub

Go to Azure portal and create a event_hubs namespace that has **Kafka enabled** (important).
Create a new event_hub in the namespace for testing and copy the connection string for your event_hub to clipboard. See screenshot for example:

![Event Hub Connection string](documentation/screenshots/event_hub_connection_string.png?raw=true "Event Hub Connection string")

#### Put event hub connection string into local config

Open "local_config.yaml" in your favorite editor and make sure to paste your event hub connection string for the key "LATIGO_INTERNAL_EVENT_HUB"

#### Set up environment from local_config

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

> NOTE: If you want to know what the configuration options mean, please see the [available parameter sections](#available-parameter-sections)

#### Start docker compose

You can use docker-compose directly or you can use the [Makefile](#makefile). Please keep in mind that the Makefile is a convenience wrapper and will be explained after the docker-compose basics have been covered.

```bash
# Start the services
docker-compose up
```

At this point you should see the services running:

- latigo-scheduler
- latigo-executor-1
- latigo-executor-2

#### Rebuilding services

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

#### Makefile

There is a makefile in the project that is meant as a convenience to save time, and also as a reference for commands. To see the commands, simply open it in a text editor. The Makefile is made to be self-documenting, to see what it contains, simply invoke it without a target like so:

```bash
make
```

### Connecting directly to Gordo

#### About Gordo
Gordo is the actual prediction engine that Latigo will lean on to get work done. Gordo is a kubernetes cluster, and you will need access to this cluster for Latigo to be usefull.

There are some things you need to know about Gordo up front:

- Gordo is in active development
- At the time of writing (2019-10-17) there currently exists no Gordo in "production", however many candidate clusters are running. You will have to communicate with Gordo team to find out which of their test/dev clusters are the best to be using while testing. Some are more stable than others.
- If you need to access Gordo directly during development for debugging purposes you can use port forwarding. This is documented below.
- Latigo will connect to Gordo and Time Series API using [Equinor API Gateway](https://api.equinor.com/) and wil use a so called "bearer token" for authentication.

#### Disable proxy
Before you can have portforwarding set up successfully, you need to disable proxy settings (Gordo is available via external network). For more information about proxy setup in Equinor please see [equinor wiki](https://wiki.equinor.com/wiki/index.php/ITSUPPORT:Linux_desktop_in_Statoil#Proxy_settings).

```bash
# Disable proxy (NOTE: if you don't have unset proxy, read the documentation as described above)
unsetproxy
```

#### Log in to Azure

```bash
az login
```
> NOTE: At this point you should see a list of subscriptions that you have access to in the terminal. Make sure you see the subscription(s) you expect to be working with.

#### Select active subscription
```bash
# To see the list of available subscriptions you can use the command:
az account list

# Now select active subscription.
az account set --subscription "019958ea-fe2c-4e14-bbd9-0d2db8ed7cfc"

# Make sure the correct one is set
az account show
```
> NOTE: We used "Data Science POC - Non production" in this example which is the correct one to use at the time of writing (2019-10-21).

#### Install azure AKS tools
```bash
# If you don't have aks tools such as kubectl and other commands, install it like this:
az aks install-cli
```
> NOTE: You only need to do this once


#### Select cluster
```bash
# Now we can tell aks to focus on one particular cluster
az aks get-credentials --overwrite-existing --resource-group gordotest28 --name gordotest28 --admin
```
> NOTE: Here we used "gordotest28" as a placeholder for the actual cluster name that you will use. Please ask Gordo team which cluster that is recommende for use

#### Select context
Now that we have selected which cluster to work with we can start sending commands to it with kubectl
```bash
# Set the kubernetes context with namespace
kubectl config set-context --current --namespace=kubeflow
```

#### List Gordo projects
```bash
# Now we can list all the "Gordo projects" running in this cluster
kubectl get gordos
```

#### Set up port forwarding to Gordo cluster
This is useful when manually debugging with Gordo, but you should not rely on it for interfacing Latigo with Gordo, for that use a proper connection through API Gateway.

```bash
# Now we set up port forwarding so that our code can talk to the cluster
kubectl port-forward svc/ambassador -n ambassador 8080:80
```
> NOTE: Here 8080 is the port you want to use locally. Feel free to use whatever port is convenient for you.
To terminate the port forwarding simply stop the process with <ctrl>+<C>.

> NOTE: The port forwarding can be flaky and will likely quit at random. To overcome the frustration, you can use the command below:
```bash
# Put portforwarding in infinite loop so it is restarted whenever it go down unexpectedly
make port-forward
```

*To verify that the connection works, you can open the URL for a Gordo project in the browser:*
```bash
xdg-open http://localhost:8080/gordo/v0/ioc-1130/
```
> NOTE: Please make sure to use correct port and project name. We used "8080" and "ioc-1130" as placeholders in the example.

🍰 Now you should see a browser full of metadata in json format signaling that you are now ready to connect to cluster from code!

### Requirement pinning

We use **requirements.in** and **requirements.txt** files to keep track of dependencies. requirements.in is the version ranges we want. We use make file to convert this into requirements.txt which are the exactly pinned requirements.

```bash
# Rebuild requirements.txt from requirements.in
make req
```

>NOTE: Both requirements.in and requirements.txt are kept in git

## Deployment

Deployment is handled by the [latigo Kustomize project](W/equinor/latigo-k8s).

