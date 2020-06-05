# Latigo - Continuous Prediction Service

## Table of content
* [About](#about)
  * [History](#History)
* [Developer manual](#Developer-manual)
  * [Architecture](#Architecture)
    * [Scheduler](#Scheduler)
    * [Executor](#Executor)
  * [Proxy setup](#Proxy-setup)
  * [How to run locally (pain part..)](#How-to-run-locally-(pain-part..))
  * [How to run image locally](#How-to-run-image-locally)
  * [How to login to different resources](#How-to-login-to-different-resources)
    * [Login to azure](#Login-to-azure)
    * [Login to docker](#Login-to-docker)
    * [Access Kubernetes](#Access-Kubernetes)
  * [Requirement pinning](#Requirement-pinning)
  * [How to update Latigo on the k8s cluster](#How-to-update-Latigo-on-the-k8s-cluster)
    * [Make new Latigo version](#Make-new-Latigo-version)
    * [Run new image version on the k8s](#Run-new-image-version-on-the-k8s)
    * [Update secrets on the k8s](#Update-secrets-on-the-k8s)
* [Latigo configurations](#Latigo-configurations)
  * [Configuration files](#Configuration-files)
  * [Available parameter sections](#Available-parameter-sections)
* [Run Tests](#Run-Tests)
* [License](#License)
* [TODOs](#TODOs)

==================================

## About

Latigo is a service that is responsible for continuously running machine learning algorithms on a set of input sensor data to predict the next datapoint in sensor data. This is useful to do predictive maintenance for industrial equipment.

Latigo is a small part of a larger system developed for [Equinor](https://equinor.com).

Common flow is written on the [wiki](https://wiki.equinor.com/wiki/index.php?title=OMNIA.prevent#Latigo_-_Prediction_service)

### History

This project has been based on the original prototype project [ioc-gordo-oracle](/equinor/ioc-gordo-oracle) and has since evolved to support other needs and technologies.


## Developer manual

This section will explain the structure of the project from a technical perspective and then how to start development for Latigo.

### Architecture

Latigo is a distributed application with two nodes:

- Scheduler
- Executor

For connecting to Equinor services Latigo uses [session request library](https://github.com/equinor/requests_ms_auth)

#### Scheduler
Main objective of the Scheduler is to create one "task" for making a prediction for each model for certain time-range repeatedly. 

##### [Scheduler`s flow](https://wiki.equinor.com/wiki/index.php?title=OMNIA.prevent#Scheduler)

#### Executor
Main objective of the Executor is to make a predictions and store it results (based on the "tasks" from Scheduler).

##### [Executor`s flow](https://wiki.equinor.com/wiki/index.php?title=OMNIA.prevent#Executor)

##### Executor`s errors handling 
Might be found on [wiki](https://wiki.equinor.com/wiki/index.php?title=OMNIA.prevent#Executor.60s_errors_handling).

### Proxy setup
This on ONLY if you are on Equinor computer.  
If you are on Equinor computer might be needed to disable/enable proxy.  
Several services that you will be using are available over public networks only and the proxy setup for Equinor might get in the way.  
To prevent this you must install a means to enable and disable the proxy on your platform. This has been documented in the [equinor wiki](https://wiki.equinor.com/wiki/index.php/ITSUPPORT:Linux_desktop_in_Statoil#Proxy_settings).

Once this has been successfully set up, you can use the following:
```bash
# Disable proxy
unsetproxy
# Enable proxy
setproxy
```

### How to run locally (pain part..)

For 2020.05.08 there's no easy way to run Latigo locally without pain and digging into code.  
This is because Latigo for initially designed as library (but is not uses as one and imports were not properly made).  

In short to run Latigo you have to do few points:
- ask for the files with credentials from your teammates:
  - scheduler_local.yaml (note that `run_at_once` parameter is very helpful in the development cycle, see [scheduler](#scheduler) section for details;
  - executor_local.yaml.
- set up you OWN event hub (do not use production one or one of your colleges):
  - Go to Azure portal and create a event_hubs namespace that has **Kafka enabled** (important).
  - Create a new event_hub in the namespace for testing and copy the connection string for your event_hub to clipboard. See screenshot for example:
    - ![Event Hub Connection string](documentation/screenshots/event_hub_connection_string.png?raw=true "Event Hub Connection string")
  - paste your event hub connection string (with following structure **Endpoint=sb://some_bus_name.servicebus.windows.net/;SharedAccessKeyName=some_name;SharedAccessKey=some_access_key;EntityPath=some_path**) in their respective **task_queue** sections in: 
    - executor_local.yaml
    - scheduler_local.yaml
    ```yaml
    task_queue:
        connection_string: <Your event hub connection string>
    ```
- set credentials for [Azure Redis cache](https://github.com/Azure/open-service-broker-azure/blob/master/docs/modules/rediscache.md):
  - to determine what if particular Redis for DEV or PROD env: got to `Tag` tab in Redis on Azure portal and see `ENV` tag:
    - in case you need to get keys for connection - run `kubectl -n latigo get secret dev-azure-rediscache-instance-secret -o yaml`. Then decode needed value `echo password | base64 -D`.
  - how to get credentials [article](https://docs.microsoft.com/en-us/azure/azure-cache-for-redis/cache-how-to-redis-cli-tool)
  - export proper variables:  
  ```shell script
  export CACHE_HOST=REPLACE_ME
  export CACHE_PASSWORD=REPLACE_ME
  export CACHE_PORT=REPLACE_ME
  ```
- install the requirements (almost never works from first time);
- dig into code to understand the "magic" and why Makefile commands or other commands do not see the config files;
- as the result you should see in logs that:
  - for scheduler: that some amount of messages to the Kafka where sent and you see them in you Azure queue;
  - for executor: after messages where delivered to Kafka you'll see processing of the messages and that predictions are executing and storing.
- enjoy :)
 
P.S. such approach of starting the development for newcomers can be fixed by "closing" [TODOs](#TODOs) section. 

Also, for available commands check [Makefile](/equinor/latigo/blob/master/Makefile). But be aware that they might do not work as designed.


### How to run image locally
Few things to take into account:
- certificate path `ssl.ca.location` in the `*_local.yaml` config files for `task_queue` should be:
  - for running locally: `"/usr/local/etc/openssl/cert.pem"`;
  - for running in the container: `"/etc/ssl/certs/ca-certificates.crt"`.
- following env variables should be exported:
```shell script
export LATIGO_EXECUTOR_CONFIG_FILE=../executor_local.yaml
export LATIGO_SCHEDULER_CONFIG_FILE../scheduler_local.yaml
```
Add credentials for cache:
```docker
# put this to docker-compose.yaml to `environment` section file or export them as you wish
- CACHE_HOST=REPLACE_ME
- CACHE_PASSWORD=REPLACE_ME
- CACHE_PORT=REPLACE_ME
```

- run:
```shell script
docker-compose build --no-cache .
docker-compose up -d --remove-orphans
```

### How to login to different resources

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

#### Access Kubernetes

##### Install azure AKS tools
```bash
# If you don't have aks tools such as kubectl and other commands, install it like this:
az aks install-cli
```

##### Select cluster
```bash
# Now we can tell aks to authenticate with one particular cluster
az aks get-credentials --overwrite-existing --resource-group <cluster name> --name <cluster name> --admin
# And set our context to only show the relevant resources for all future kubectl commands
kubectl config set-context --current --namespace=<namespace>
```

> NOTE: Replace the placeholder ```<cluster name>``` for the actual cluster name that you will use. Please ask Gordo team which cluster that is recommended for use.  
> NOTE: Replace the placeholder ```<namespace>``` for the actual namespace that you will use. You can use ```kubeflow``` for accessing Gordo and ```latigo``` for accessing Latigo.

##### List Latigo resources
```bash
# When you have latigo namespace set you can list all Latigo resources 
kubectl get all
```

##### List Gordo projects
```bash
# When you have gordo namespace set you can list all the "Gordo projects" running in this cluster
kubectl get gordos
```

### Requirement pinning

We use ```requirements.in``` and ```requirements.txt``` files to keep track of dependencies. ```requirements.in``` is the version ranges we want. We use make file to convert this into ```requirements.txt``` which are the exactly pinned requirements.

```bash
# Update to latest versions and rebuild requirements.txt from requirements.in
make req
```

### How to update Latigo on the k8s cluster

Note: this repo has CI as the GitHub actions that are in the `.github/workflows/` folder.

#### Make new Latigo version
If you want to push your changes to k8s:
- increase version in `VERSION` file along with your PR;
- merge PR to `master`;
- wait until GitHub actions will build and push the new image.

#### Change version of Latigo in k8s configs
After new image will be pushed to the docker registry replace old version with the new one in this [repo](https://github.com/equinor/latigo-k8s) in following files:
- `latigo-executor.yaml`
- `latigo-scheduler.yaml`

#### Run new image version on the k8s
Changes that were made on the previous step are automatically picked up by Aurora but not automatically deployed to the cluster.  
To update new version on the k8s:
- goto [Aurora](https://dashboard.internal.aurora.equinor.com/applications/aurora15-latigo) and click on `SYNC`;
- after this you should see how new pods starting creating;
- NOTE: check logs each time you update Latigo on the k8s to make sure that it's up and running.

#### Update secrets on the k8s
If you need to update secrets like `scheduler_secret.yaml` and `executor_secret.yaml` do following:
- get current secrets from cluster:
```shell script
# Note: you should be logged to the `make login-azure` and `make login-latigo`
make get-secrets
```
- make needed changes with this filed and then:
```shell script
make set-secrets
```
- after recreate the executor and scheduler pods to fetch new secrets.


## Latigo configurations

This section will guide you to how you can manage Latigo once in production.

Latigo is largely data-driven both in configuration as well as during operations.  
All parameters of the application can be adjusted via parameters in the configuration.  
This seciton outlines how you go about changing the parameters and what each parameter means.

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

| Parameter | Default | Description |
|      ---: | :-----: | :---------- |
| azure_monitor_instrumentation_key | \<key> | Instrumentation key for connecting to Azure monitor. |
| azure_monitor_logging_enabled | false | Determine if logs will be additionally sent to the Azure monitor. |
| continuous_prediction_start_time | "08:00" | The start time of scheduling. See [scheduling algorithm](#scheduling-algorithm) for details. |
| continuous_prediction_interval | "30m" | The interval of scheduling. See [scheduling algorithm](#scheduling-algorithm) for details. |
| continuous_prediction_delay | "3h" | The prediction delay of scheduling. See [scheduling algorithm](#scheduling-algorithm) for details. |
| run_at_once | False | A setting primarily used for debugging. When the scheduler program starts up, it normally will wait until a scheduling time before working. With run_at_once set to True it will always start by performing a scheduling on startup disregarding time. |
| log_debug_enabled | false | Determine if prediction execution detailed log with time measurement will be written to log. |

#### executor
| Parameter | Default | Description |
|      ---: | :-----: | :---------- |
| azure_monitor_logging_enabled | false | Determine if logs will be additionally sent to the Azure monitor. |
| azure_monitor_instrumentation_key | \<key> | Instrumentation key for connecting to Azure monitor. |
| log_debug_enabled | false | Determine if prediction execution detailed log with time measurement will be written to log. |

#### task_queue

Both scheduler and executor has a task_queue configuration. It describes their connection to azure event hub via kafka interface that allows scheduler to push tasks to executors.

| Parameter | Default | Description |
|      ---: | :-----: | :---------- |
| type | "kafka" | Currently only kafka is supported. There has been "event_hub" and "postgres" in the past. |
| connection_string | not shown | The full connection string as copied from event_hub panel in azure portal. |
| security.protocol | "SASL_SSL" | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| ssl.ca.location | "/etc/ssl/certs/ca-certificates.crt" | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| sasl.mechanism | "PLAIN" | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| group.id | "1" | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| client.id | "latigo_scheduler" | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| request.timeout.ms | 10000 | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| session.timeout.ms | 10000 | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| default.topic.config | {"auto.offset.reset": "earliest"} | See [Kafka docs](https://kafka.apache.org/documentation.html#newconsumerconfigs). |
| debug | "fetch" | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| topic | "latigo_topic" | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| enable.auto.commit | true | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| auto.commit.interval.ms | 1000 | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |
| max.poll.interval.ms | 86400000 | See [confluent docs](https://docs.confluent.io/current/installation/configuration/consumer-configs.html). |

#### auth

Auth sections are used by gordo, time_series and metadata API to do oauth2 in azure.   
They look like following but might has some differences depends on the API:

| Parameter | Default | Description |
|      ---: | :-----: | :---------- |
| resource | "set from env" | The resource ID in Azure. |
| tenant | "set from env" | The tenant ID in Azure. |
| authority_host_url | "set from env" | The authority host URL in [Azure](https://docs.microsoft.com/en-us/samples/azure-samples/data-lake-analytics-python-auth-options/authenticating-your-python-application-against-azure-active-directory/). |
| client_id | "set from env" | The client ID in Azure. |
| client_secret | "DO NOT PUT SECRETS IN THIS FILE" | The client secret in Azure. |
| verification_url | "" | Url that will be used to check if connection to the particular API was successful. |
| verification_element | "" | Element from JSON response of "verification_url" existing of what will be checked (sometimes Microsoft sends 200 and login page instead of access token). |
| auto_adding_headers | "" | Headers that will be automatically added to each request. Needed for Metadata API. |

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

#### prediction_metadata_storage
| Parameter | Default | Description |
| type | "metadata_api" | where metadata will be stored. |
| base_url | "https://aurora15.shared.aurora.equinor.com/omnia-prevent" | The base URL to use for connecting to metadata API. See [documentation](https://aurora15.shared.aurora.equinor.com/omnia-prevent/docs).|
| auth | [see the auth section](#auth) | The authentication for accessing metadata API. |


## Run Tests
To run tests - export following ENV variables with previously replaced values (this variables will be needed for integration tests):
```shell script
export METADATA_API_TENANT=tenent
export METADATA_API_CLIENT_ID=id
export METADATA_API_CLIENT_SECRET=secret
export METADATA_API_RESOURCE=resourse
export METADATA_API_AUTHORITY_HOST_URL=authority
export METADATA_API_BASE_URL=url
export METADATA_API_APIM_KEY=key
```

OR create and fill `.env` file and then apply it:
```shell script
set -a
source .env
set +a
```

OR add env variables to Pycharn or other IDE (with previously added values):
```text
METADATA_API_TENANT=tenent;METADATA_API_CLIENT_ID=id;METADATA_API_CLIENT_SECRET=secret;METADATA_API_RESOURCE=resourse;METADATA_API_AUTHORITY_HOST_URL=authority;METADATA_API_BASE_URL=url;METADATA_API_APIM_KEY=key;
```

Then run:
```
make test
```

## License

Please see [LICENSE](LICENSE) file for details. Latigo has G-Faps and is licensed under GNU AFFERO GENERAL PUBLIC LICENSE.


## TODOs
- resolve `TODOs` on the [wiki page](https://wiki.equinor.com/wiki/index.php?title=OMNIA.prevent#Latigo_-_Prediction_service);
- add Latigo ability to scale;
- fetching tag data from Time Series API [bug](https://dev.azure.com/EquinorASA/OMNIA%20Prevent/_sprints/taskboard/OMNIA%20Prevent%20Team/OMNIA%20Prevent/Sprint%208?workitem=17345) and other bugs;
- "clean" configs and the repo -> [story](https://dev.azure.com/EquinorASA/OMNIA%20Prevent/_workitems/edit/17074);
- cover repository by tests and clean the code.
