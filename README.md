# Latigo - Continuous Prediction Service

## Table of content

- [About](#about)
- [Developer manual](#developer-manual)
- [Operations manual](#operations-manual)

## About

Latigo is a service that is responsible for continuously running machine learning algorithms on a set of input sensor data to predict the next datapoint in sensor data. This is useful to do predictive maintenance for industrial equipment.

Latigo is a small part of a larger system developed for [Equinor](https://equinor.com).

### Basic operation

The basic operation follows these steps:
- Fetches **list of projects** to predict for from [Gordo](/equinor/gordo) (to be replaced by [Prevent Metadata API](/equinor/prevent-metadata-api) in the future).
- On a predefined **schedule**, perform prediction as follows:
  - Fetches the **source data** from the [Time Series API](/equinor/OmniaPlant/tree/master/Omnia%20Timeseries%20API).
  - Feed data to [Gordo](/equinor/gordo) to **generate predictions**.
  - **Store predictions** back to [Time Series API](/equinor/OmniaPlant/tree/master/Omnia%20Timeseries%20API).
  - (planned) **Store prediction metadata** to [Prevent Metadata API](/equinor/prevent-metadata-api)


### License

Please see [LICENSE](LICENSE) file for details. Latigo has G-Faps and is licensed under GNU AFFERO GENERAL PUBLIC LICENSE.

### History

This project has been based on the original prototype project [ioc-gordo-oracle](/equinor/ioc-gordo-oracle) and has since evolved to support other needs and technologies.

## Developer manual

This section will first explain the structure of the project from a technical perspective in the [architecture](#architecture) section, then go on to explain how to start development for Latigo in the [development environment](#development-environment) section.

### Architecture

Latigo is a distributed application with two nodes:

- Scheduler
- Executor

#### Scheduler

In Latigo there will be exactly one scheduler instance running. The scheduler instance will produce one "task description" for each prediction to be made. The task description will contain the following:
- Timespan for prediction
- The sensor_data tags to predict for
- The Gordo config for the prediction (which "Gordo machine" to use)

The scheduler will produce these tasks according to the schedule and feed them into an internal message queue ( [Azure Event Hub](https://docs.microsoft.com/en-us/azure/event-hubs/event-hubs-about) ).

#### Executor

In Latigo there will be one or more executor instances running. The executor instances will each pick tasks from the internal message queue and "execute" them one by one. There may be more one executor operating concurrently for scalability.

For each tasks the executors will do as follows:
- Read one tasks description.
- Find the required data for the prediction in the source ([Time Series API](/equinor/OmniaPlant/tree/master/Omnia%20Timeseries%20API)).
- Download the data required for the prediction from the source ([Time Series API](/equinor/OmniaPlant/tree/master/Omnia%20Timeseries%20API)).
- Send the data to [Gordo](/equinor/gordo) and produce prediction results.
- Download the prediction results from [Gordo](/equinor/gordo).
- Upload the prediction result to the destination ([Time Series API](/equinor/OmniaPlant/tree/master/Omnia%20Timeseries%20API)).
  - (planned) Store prediction metadata to [Prevent Metadata API](/equinor/prevent-metadata-api)

### Interfaces

To manage change, the Latigo code base has been designed around the use of the following interfaces:

#### PredictionExecutionProviderInterface
Wrap the engine that produces predictions based on sensor data (Currently implemented by [Gordo](/equinor/gordo)).
- execute_prediction(project_name: str, model_name: str, sensor_data: SensorData) -> PredictionData

[source code](/equinor/latigo/tree/master/app/latigo/prediction_execution)

#### ModelInfoProviderInterface
Wrap the source of meta data about which models should be predicted (Currently implemented by [Gordo](/equinor/gordo)).

- get_all_models(projects: typing.List)
- get_model_by_key(project_name: str, model_name: str)
- get_spec(project_name: str, model_name: str) -> typing.Optional[SensorDataSpec]:

[source code](equinor/latigo/tree/master/app/latigo/model_info)

#### SensorDataProviderInterface
Wraps the source of sensor data.
##### Interface
- get_data_for_range(spec: SensorDataSpec, time_range: TimeRange) -> SensorData

[source code](/equinor/latigo/tree/master/app/latigo/sensor_data)


#### PredictionStorageProviderInterface
Wraps the destination where predictions are stored (currently implemented by [Time Series API](/equinor/OmniaPlant/tree/master/Omnia%20Timeseries%20API)).
- put_prediction(prediction_data: PredictionData)

[source code](/equinor/latigo/tree/master/app/latigo/prediction_storage)

### Development environment

#### Prequisites

You will need the following:
- Git with authentication set up ([howto](https://wiki.equinor.com/wiki/index.php/Software:Git_Tutorial_Getting_Setup))
- Python 3.x
- Docker and docker-compose installed ([howto](https://wiki.equinor.com/wiki/index.php/WIKIHOW:Set_up_Docker_on_a_CentOS_7_server))
- Connection string to Azure Event Hub and both read/write permission to it ([howto](#set-up-event-hub))
- Connection string to [Time Series API](/equinor/OmniaPlant/tree/master/Omnia%20Timeseries%20API)
- If you are on Equinor computer, a means to disable/enable proxy ([howto](#proxy-setup))

#### Proxy setup
Several services that you will be using are available over public networks only and the proxy setup for Equinor might get in the way.

To prevent this you must install a means to enable and disable the proxy on your platform. This has been documented in the [equinor wiki](https://wiki.equinor.com/wiki/index.php/ITSUPPORT:Linux_desktop_in_Statoil#Proxy_settings).

Once this has been successfully set up, you can use the following:
```bash
# Disable proxy
unsetproxy
# Enable proxy
setproxy
```

#### Clone project and enter project folder

```bash
# Go to where you keep your projects
cd ~/Desktop/Projects
# Fetch the sources from github
clone git@github.com:equinor/latigo.git
# Go into newly created latigo project folder
cd latigo
```

#### Makefile

There is a [Makefile](https://en.wikipedia.org/wiki/Make_(software)) in the project that is meant as both a convenience to save time, and also as a reference for many common commands. To see the commands, simply open the [Latigo Makefile](/equinor/latigo/blob/master/Makefile) in a text editor. The Makefile is made to be self-documenting, to see what it contains, simply invoke it without a target like so:

```bash
# Show the menu of commands available
make
```
#### Create local configuration file
To be able to run Latigo locally it will need a valid configuration. To help you manage this during development there is a script called [set_env.py](set_env.py) that will set environment variables that are needed by Latigo stored in the file [local_config.yaml](local_config.yaml).

Just after cloning Latigo, you will want to run [set_env.py](set_env.py) to have it generate a [local_config.yaml](local_config.yaml) for you:
```bash
# Create local config if it does not exist
./set_env.py

# Edit the file to put the correct values
nano local_config.yaml
```
Set the values as follows
```yaml
DOCKER_PASSWORD: <Your password for docker registry>
DOCKER_REGISTRY: <Your hostname of docker registry>
DOCKER_REPO: <Your name of the repository in docker registry>
DOCKER_USERNAME: <Your username for docker registry>
LATIGO_EXECUTOR_CONFIG_FILE: /app/executor_local.yaml
LATIGO_SCHEDULER_CONFIG_FILE: /app/scheduler_local.yaml
```
> NOTE: The "/app/" part of the path is where [docker-compose.yml](docker-compose.yml) will mount the file inside the docker images.

The next step is to make copies of the default configuration files like so:

```bash
cp deploy/executor_config.yaml executor_local.yaml
cp deploy/scheduler_config.yaml scheduler_local.yaml
```
> NOTE: Make sure the name of the files are identical to the ones referenced from local_config.yaml

Next, edit the files in turn

```bash
nano executor_local.yaml
nano scheduler_local.yaml
```
Remove all settings from the configurations not marked "CHANGE ME" while retaining the structure of the files. For example:

```yaml
sensor_data:
    type: "time_series_api"
    base_url: "https://api.gateway.equinor.com/plant-beta/timeseries/v1.5"
    async: False
    auth:
        resource: "CHANGE ME"
        tenant: "CHANGE ME"
        authority_host_url: "CHANGE ME"
        client_id: "CHANGE ME"
        client_secret: "CHANGE ME"
        scope: ['read', 'write']
```
would become

```yaml
sensor_data:
    auth:
        resource: "<Your resource>"
        tenant: "<Your tenant>"
        authority_host_url: "<Your url>"
        client_id: "<Your client id>"
        client_secret: "<Your client secret>"
```
> NOTE: You should NOT change the default files as these are maintained in git. The local configuration files will be "overlaid" over the defaults. Please see [configuration files](#configuration-files) section for details.

> NOTE: You should NOT put your local copies into git

Every detail of the configuration is exhaustively covered in the [configuration files](#configuration-files) section so in this section we have only focused on the details important for the developer.

#### Set up event hub

Go to Azure portal and create a event_hubs namespace that has **Kafka enabled** (important).
Create a new event_hub in the namespace for testing and copy the connection string for your event_hub to clipboard. See screenshot for example:

![Event Hub Connection string](documentation/screenshots/event_hub_connection_string.png?raw=true "Event Hub Connection string")

#### Put event hub connection string into configuration

Edit the local configuration files in turn 

```bash
nano executor_local.yaml
nano scheduler_local.yaml
```
paste your event hub connection string on the form **Endpoint=sb://some_bus_name.servicebus.windows.net/;SharedAccessKeyName=some_name;SharedAccessKey=some_access_key;EntityPath=some_path**  in their respective **task_queue** sections:

```yaml
task_queue:
    connection_string: <Your event hub connection string>
```yaml

#### Put Gordo connection string and auth into configuration

Edit the local configuration files in turn 

```bash
nano executor_local.yaml
nano scheduler_local.yaml
```
Paste your Gordo connection string on the form **[https://ioc.dev.aurora.equinor.com/gordo/v0/](https://ioc.dev.aurora.equinor.com/gordo/v0/)** and Gordo authentication parameters in their respective **model_info** and **predictor** sections. Example for model_info:

```yaml
model_info:
    connection_string: "<gordo connection string>"
    auth:
        resource: "<gordo resource>"
        tenant: "<gordo tenant>"
        authority_host_url: "<gordo authority url>"
        client_id: "<gordo client id>"
        client_secret: "<gordo client secret>"
```yaml


##### About Gordo
Gordo is the actual prediction engine that Latigo will lean on to get work done. Gordo is a kubernetes cluster, and it may be useful to access to this cluster while debugging.

There are some things you need to know about Gordo up front:

- Gordo is in active development
- At the time of writing (2019-10-17) there currently exists no Gordo in "production", however many candidate clusters are running. You will have to communicate with Gordo team to find out which of their test/dev clusters are the best to be using while testing. Some are more stable than others.
- If you need to access Gordo directly during development for debugging purposes you can use port forwarding. This is documented below.
- Latigo will connect to Gordo and Time Series API using [Equinor API Gateway](https://api.equinor.com/) and will use a so called "bearer token" for authentication.

> NOTE: If you are having network issues, please see the section about [disabling proxy](#proxy-setup)


#### Put time series API base URL and auth into configuration

Edit the local configuration files in turn 

```bash
nano executor_local.yaml
nano scheduler_local.yaml
```
Paste your time series API base URL on the form **[https://api.gateway.equinor.com/plant/timeseries/v1.5](https://api.gateway.equinor.com/plant/timeseries/v1.5)** and time series API authentication parameters in their respective **sensor_data** and **prediction_storage** sections.  Example for sensor_data:

```yaml
sensor_data:
    base_url: "<time series connection string>"
    auth:
        resource: "<time series resource>"
        tenant: "<time series tenant>"
        authority_host_url: "<time series authority url>"
        client_id: "<time series client id>"
        client_secret: "<time series client secret>"
```yaml

#### Set up environment from local_config

Every time your local_config.yaml is changed you should use the following steps set the values from local_config.yaml into your current environment:

```bash
# See that your changes in config are reflected in output
./set_env.py

# Load environment variables from local_config.yaml into current shell session
eval $(./set_env.py)

# see that environment was actually set
env | grep LATIGO
env | grep DOCKER
```

Now your environment is set up and docker-compose will use and pass this environment on to the nodes to let them function correctly.

#### Login to azure
You need to authenticate with azure to contact kubernetes (AKS) with kubectl command. You will also need to for docker function correctly.

```bash
# Login to azure.
make login-azure
```
 > NOTE: This may open a login page in your browser
 
#### Login to docker
You need to authenticate with docker repository for accessing images there using docker and docker-compose commands.
```bash
# Login to docker repository
make login-docker
```
#### Build and run

```bash
# Build and start latigo locally
make up
```

At this point you should see the services running:

- latigo-scheduler
- latigo-executor-1
- latigo-executor-2


### Access Kubernetes

#### Install azure AKS tools
```bash
# If you don't have aks tools such as kubectl and other commands, install it like this:
az aks install-cli
```
> NOTE: You only need to do this once

#### Select cluster
```bash
# Now we can tell aks to authenticate with one particular cluster
az aks get-credentials --overwrite-existing --resource-group <cluster name> --name <cluster name> --admin
# And set our context to only show the relevant resources for all future kubectl commands
kubectl config set-context --current --namespace=<namespace>
```

> NOTE: Replace the placeholder ```<cluster name>``` for the actual cluster name that you will use. Please ask Gordo team which cluster that is recommended for use.

> NOTE: Replace the placeholder ```<namespace>``` for the actual namespace that you will use. You can use ```kubeflow``` for accessing Gordo and ```latigo``` for accessing Latigo.


#### List Latigo resources
```bash
# When you have latigo namespace set you can list all Latigo resources 
kubectl get all
```

#### List Gordo projects
```bash
# When you have gordo namespace set you can list all the "Gordo projects" running in this cluster
kubectl get gordos
```

🍰 

### Requirement pinning

We use ```requirements.in``` and ```requirements.txt``` files to keep track of dependencies. ```requirements.in``` is the version ranges we want. We use make file to convert this into ```requirements.txt``` which are the exactly pinned requirements.

```bash
# Update to latest versions and rebuild requirements.txt from requirements.in
make req
```
> NOTE: Both ```requirements.in``` and ```requirements.txt``` are kept in git

## Operations manual

This section will guide you to how you can manage Latigo once in production.

> NOTE: Developers might find [Development manual](#development) sections of interest.

Latigo is largely data-driven both in configuration as well as during operations. All parameters of the application can be adjusted via parameters in the configuration. This seciton outlines how you go about changing the parameters and what each parameter means.

### Configuration files

All settings are stored in yaml configuration files. The default values are stored in git:

- [app/deploy/scheduler_config.yaml](app/deploy/scheduler_config.yaml)
- [app/deploy/executor_config.yaml](app/deploy/executor_config.yaml)

During application initialization these values are loaded as the basis of the configuration and then extended by another set of configuration files identified by the environment variables for scheduler and executor respectively:

1. **LATIGO_SCHEDULER_CONFIG_FILE**
2. **LATIGO_EXECUTOR_CONFIG_FILE**

In production these files are stored in azure vault. Go to azure vault and edit the configurations for *scheduler* and *executor* respectively:
1. **latigo-scheduler-config-yaml**
2. **latigo-executor-config-yaml**

> TIP: You can use make set-secrets to propegate changes to secrets quickly, and conversely get-secrets to view them. See the [Makefile](/equinor/latigo/blob/master/Makefile) for how this works.

The meaning of each configuration parameter is documented below.

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
| run_at_once | False | A setting primarily used for debugging. When the scheduler program starts up, it normally will wait until a scheduling time before working. With run_at_once set to True it will always start by performing a scheduling on startup disregarding time. |

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
| type | "time_series_api" | The source to use for sensor data. Currently only "time_series_api" is supported. There has been "influx" in the past. |
| base_url | "https://api.gateway.equinor.com/plant-beta/timeseries/v1.5" | The base URL to use for connecting to time_series_api. See documentation [here](https://api.equinor.com/docs/services/Timeseries-api-v1-5).|
| async | False | Wether or not to use async calls to time_series_api. Currently only False is tested. |
| auth | [see the auth section](#auth) | The authentication for accessing time_series_api. |

#### prediction_storage

| Parameter | Default | Description |
|      ---: | :-----: | :---------- |
| type | "time_series_api" | The sink to use for storing predction data. Currently only "time_series_api" is supported. There has been "influx" in the past. |
| base_url | "https://api.gateway.equinor.com/plant-beta/timeseries/v1.5" | The base URL to use for connecting to time_series_api. See documentation [here](https://api.equinor.com/docs/services/Timeseries-api-v1-5).|
| async | False | Wether or not to use async calls to time_series_api. Currently only False is tested. |
| auth | [see the auth section](#auth) | The authentication for accessing time_series_api. |

### Scheduling algorithm

The idea is that tasks are scheduled at a predictable wall clock time, so you know that for example "Every day at 09:30 a new prediction will be performed".

The scheduler operates using the following algorithm:

1. Get the current time of day into `NOW`
2. Get value of `continuous_prediction_start_time` into `X`
3. Add value of `continuous_prediction_interval` to `X` until `X` > `NOW`
4. Set `Y` = `X` - `NOW`
5. Wait until `Y` time passes
6. Queue up tasks for each project in the interval  `continuous_prediction_interval`, going back `continuous_prediction_delay` in time.
7. Repeat

Deployment of Latigo is handled by the [Latigo Kustomize project](W/equinor/latigo-k8s).

### Run Tests
To run tests - export following ENV variables (with previously replaced values):
```shell script
export METADATA_API_TENANT=tenent
export METADATA_API_CLIENT_ID=id
export METADATA_API_CLIENT_SECRET=secret
export METADATA_API_RESOURCE=resourse
export METADATA_API_AUTHORITY_HOST_URL=authority
export METADATA_API_BASE_URL=url
export METADATA_API_APIM_KEY=key
```

OR add env variables to Pycharn or other IDE (with previously added values):
```text
METADATA_API_TENANT=;METADATA_API_CLIENT_ID=;METADATA_API_CLIENT_SECRET=;METADATA_API_RESOURCE=;METADATA_API_AUTHORITY_HOST_URL=;METADATA_API_BASE_URL=;METADATA_API_APIM_KEY=;
```

Then run:
```
make test
```


