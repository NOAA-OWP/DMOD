# Contents
* [Initial Setup for Docker Desktop Environment](#initial-setup-for-docker-desktop-environment)
* [Initial Setup for Non-Desktop Environment](#initial-setup-for-non-desktop-environment)
* [Link to More MinIO Documentation](#for-more-info-on-minio-configuration)

****
****
## Initial Setup for Docker Desktop Environment

The basic steps for initially setting up the MinIO service in a development environment that uses Docker Desktop are summarized as:

* [Install the `mc` Client](#install-the-mc-client)
* [Create Secrets Files](#create-secrets-files)
* [Configure Environment Variables](#configured-environment-variables)
* [Start the Object Store DMOD Stack](#start-the-stack)
* [Initialize User Access via Helper Script](#run-helper-script-to-initialize-user-access)

#### Note on Config File Names
The `./scripts/control_stack.sh` script will attempt to detect when a system is running on Docker Desktop.  When this is the case, the script will prioritize deploying using a config named `docker-single-node.yml`, if such a file is available.

MinIO supports High Availability configurations using several nodes, and generally this is what is wanted in a DMOD deployment.  However, this can't be run on Docker Desktop, because a Docker Desktop Swarm can only support a single node.  As such, a separate deployment config was created to support working with the object store stack in Desktop development environments.

****
### Install the `mc` Client

At present, the only ways to perform certain required tasks for setup of MinIO in DMOD is either via the web console or the `mc` client.   To use the included setup helper script (i.e., the method documented here), the `mc` client is required.

The [MinIO Client Complete Guide](https://docs.min.io/docs/minio-client-complete-guide) has instructions for installing the client on various platforms.

****
### Create Secrets Files

Create the directory `docker/secrets/object_store/`.  This can be done from the project root with

```
mkdir -p docker/secrets/object_store/
```

Then create these files within that directory, with the contents described below.

* `access_key` - the admin user name for MinIO (suggest: minioadmin)
* `secret_key` - the admin user password for MinIO
* `model_exec_access_key` - the dataset access user name for model execution workflows
* `model_exec_secret_key` - the dataset access user password for model execution workflows

Note that these files should be ignored by Git, but it is a good practice to confirm this.  THESE FILES ARE NOT TO BE COMMITTED!
****
### Configured Environment Variables

Certain variables within `.env` (or other environment config) must or may be set to configure certain behavior.

##### Storage
The data storage volume must be configured via the `DMOD_OBJECT_STORE_HOST_DIR_1` environment variable.  This can either be a host directory path or the name of an already-existing Docker Volume.

There is `DMOD_OBJECT_STORE_HOST_DIR_2` as well, but it is not currently used in the Docker Desktop deployment (it is, however, required for the more general HA deployment).

##### Optional: Host Port Forwards
Docker host ports that will receive port forward mappings may optionally be configured.  The `DMOD_OBJECT_STORE_1_CONSOLE_HOST_PORT` environment variable sets the port of the forwarded MinIO web console, and the `DMOD_OBJECT_STORE_1_HOST_PORT` variable sets the forwarded MinIO application port.  Defaults for these are set by the Docker deployment config if they are not supplied.

****
### Start the Stack
```
./scripts/control_stack.sh object_store deploy
```
****
### Run Helper Script to Initialize User Access

The script [scripts/minio_init.sh](../../scripts/minio_init.sh) can be used to initialize things automatically:

```
./scripts/minio_init.sh
```

There are options available (view using `--help`), but generally the defaults are good.

Necessary user accounts and access should now be in place.

*****
*****
## Initial Setup for Non-Desktop Environment

As [noted above](#note-on-config-file-names), there are some differences that require a different deployment config when deploying to a Docker Swarm not running on Docker Desktop.  In those cases, the `docker-compose.yml` deployment config will be used.

In general, the setup process is very similar to that of [the Desktop setup](#initial-setup-for-docker-desktop-environment). Some known differences are:
* There must be at least two Swarm nodes, with a node hosting _at most_ one the two Docker services running the MinIO application, named `minio1` and `minio2`
  * These two nodes must be designated by applying the `minio1` and `minio2` Docker labels respectively
* The required `DMOD_OBJECT_STORE_HOST_DIR_1` and `DMOD_OBJECT_STORE_HOST_DIR_2` values for [storage configuration](#configured-environment-variables) must be valid on both Swarm nodes
  * When host directories for bind mounts, they must exist on both nodes
  * When Docker volumes, they must be created in advance on each node
* Host port forwards can be set up for MinIO app and web console of the `minio2` service instance, though there are reasonable defaults
* The Docker label `object_store_proxy` must be applied to the Swarm node that should host the proxy service for the object store

****
****
## For more info on MinIO configuration

[see the documentation here](https://docs.min.io/docs/minio-server-configuration-guide.html)
