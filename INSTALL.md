# Installation instructions

Detailed instructions on how to install, configure, and get the project running.

# TL;DR

- Install project [dependencies](doc/DEPENDENCIES.md)
  - Optionally, setup and use a [dedicated Python virtual environment](#using-a-virtual-environment) (highly recommended)
- Create a [customized local environment config](#local-environment-configuration), manually or using a [helper script](#environment-configuration-helper-script)
- Create [required Docker networks](#creating-required-docker-networks)
- Set up the [required SSL certificates](#local-ssl-certs), potentially using a helper script to [initialize all needed certs in the required directories](#setting-up-directories-and-certificates)
- Create [job worker SSH keys](#create-job-worker-ssh-keys)
- Build and install necessary [internal Python packages](#python-packages-and-dependencies) into Python environment, typically using the [provided helper script](#using-update_packagesh-for-dependencies-and-internal-packages)
- Manually create or double check [Docker secrets files](#docker-secrets-files)
- Update nodes appropriately to [satisfy deployment constraints](#applying-swarm-constraint)
- [Build Docker images](#docker-images)
- Run initial [object store setup](#object-store-setup)
- Configure [available compute resources for the scheduler](#the-scheduler-service-resource-configuration)
- Configure [images and domains](#the-scheduler-images-and-domains-configuration) for the scheduler

## Local Environment Configuration

Each local deployment and/or development environment requires its own configuration be set up in order to function properly.  This is currently done via a local environment file.  

Because of its custom nature and potentially sensitive contents, local environment configs should never be committed to the Git repo.  As such, one must be custom built for a given environment.

### File Name and Path

The general recommendation is to name this file `.env` and place it in the project root on development systems.  This is the expected default for many DMOD management script and tools.  The Git repo is also configured to ignore this path.

However, most DMOD management tools support an optional parameter for setting a custom path to an environment config, so a file can be named or located elsewhere if needed.

### Environment Configuration Helper Script

There is a simple helper script at `scripts/create_env_config.sh` that will automatically create a complete config at `.env` based on the [example.env](example.env) template file.  It is suitable for most starter deployments.   More advanced DMOD usage will require understanding and customizing the environment config, although you can still begin using the config this script produces.

### Creating Environment Config Manually

The environment config can also be created by copying the [example.env](example.env) template file and editing it as needed.  This template file contains comments explaining what the properties are and how they are used.

## Creating Required Docker Networks

A Docker-Swarm-based DMOD deployment currently requires [several Docker networks](#about-the-required-docker-networks) be set up for different communication with and between the services and job workers.  These networks are set up automatically by the `.scripts/control_stack.sh` tool, based on values in the [local environment config](#local-environment-configuration).  

Network config values (and possibly, a [manually constructed config-only network](#special-options-for-mpi-worker-network)) should be set up before running the control script.  However, the networks can be manually removed and re-created, either manually or automatically on subsequent script execution.

### Special Options for MPI Worker Network
Special options are available for the MPI worker network to support higher performance via the MACVLAN network driver.  These are `DOCKER_MPI_NET_USE_CONFIG` and `DOCKER_MPI_NET_VXLAN_ID`.  

To utilize this, a user must first *manually* create a Docker config-only network (essentially, pre-stage the config).  This is done by adding the `--config-only` flag to `docker network create`, along with the other required args.  The name of this config must also match the network name in `DOCKER_MPI_NET_NAME`, with the suffix of `-config` appended.

If `DOCKER_MPI_NET_USE_CONFIG=true`, the MPI worker network will be created using the MACVLAN driver (unless the driver itself is overridden in the config), using the provided VXLAN id value.

### About the Required Docker Networks

The networks are:

- (MPI) Job Worker Network 
  - Purpose: job worker communication, with other workers or something external (e.g., object store data source)
  - Default name: `mpi-net`
- Requests Network
  - Purpose: external communication, primarily for receiving requests
  - Default name: `requests-net`
- Main Internal Services Network
  - Purpose: service-to-service communication
  - Default name: `main-internal-net`

## Local SSL Certs

### About Service SSL Directories
Several service components of DMOD require SSL certificates to secure incoming connections.  It is acceptable for these to be self-signed.  DMOD expects these to be within several service-specific sub-directories, under a top-level SSL directory.  Assuming the top-level directory is named `ssl/`, the structure is as follows:

```
ssl
├── data-service
│    ├── certificate.pem
│    └── privkey.pem
├── evaluation-service
│    ├── certificate.pem
│    └── privkey.pem
├── local
│    ├── certificate.pem
│    └── privkey.pem
├── partitioner-service
│    ├── certificate.pem
│    └── privkey.pem
├── request-service
│    ├── certificate.pem
│    └── privkey.pem
└── scheduler-service
     ├── certificate.pem
     └── privkey.pem
```

Note that the `local/` directory is primarily for tests, rather than a service.

As illustrated, each service sub-directory must then contain two files:

* _certificate.pem_ 
  * the actual SSL certificate 
* _privkey.pem_ 
  * the private key used to create the certificate

### Setting Up Directories and Certificates

The included [gen_cert.sh](scripts/gen_cert.sh) script under `scripts/` can be used to automatically initialize the above required structure, including self-signed certificates, using its `-init` option.  E.g.:

```bash
# Uses 'ssl/' within working dir as top-level SSL dir, creating if necessary
# Add '-d <dir_name>' to use a different existing directory
./scripts/gen_certs.sh -init -email "yourAddress@email.com"
```

See the `./scripts/gen_certs.sh --help` for more details on the scripts options.

> [!NOTE]
> Users are always free to manually create the directory structure and obtain (or individually create with `gen_certs.sh`) the required certificate files.

> [!IMPORTANT]
> Users must configure the deployment environment properly, such that `DMOD_SSL_DIR` in the config points to the aforementioned top-level directory. 

## Create Job Worker SSH Keys
The job worker containers require SSH keys in order to communicate with each other during an MPI job.  The location of these is configurable in the local environment, specifically under `DOCKER_BASE_IMAGE_SSH_HOST_DIR` and `DOCKER_NGEN_IMAGE_SSH_HOST_DIR`.

The `./scripts/control_stack.sh` script will automatically create directories and keys as needed according to the environment config.  Alternatively, the keys can be manually created and placed in these directories, although they must not require a password and be named `id_rsa`.

# Python Development

## Installing Python and Path Verification

As noted in the [dependencies](doc/DEPENDENCIES.md), Python, the Python development package, and Pip should be installed in the appropriate manner for your environment.  

### Different Python Executable Names
It is quite common for the Python executables to be named `python3`, `python311`, `pip3`, etc. in the *global* Python environment, instead of just `python` and `pip`.  This is accounted for when [creating a virtual environment](#using-a-virtual-environment), provided the right Python command was used to create it.  Users not doing this should consider setting up shell aliases, symlinks in their path, or some other mechanism to ensure `python` and `pip` execute the desired versions appropriately.

> [!NOTE]
> DMOD components and documentation may assume use of `python` or `pip`. 

## Using a Virtual Environment

It is recommended that contributors use a Python virtual environment if they intend to do development on the Python source code used by the project.  This is not an absolute requirement, but typically is appropriate. 

```bash
# Typically it's best to run this from within the local DMOD repo directory
python -m venv venv
```

> [!IMPORTANT]
> As [discussed above](#different-python-executable-names), before creating the virtual environment, verify *both* that `python` executes **AND** that it executes the right version.

The project is tested to work with environments created by the `venv` module.  Additionally, it is recommended the directory be either located outside the project root or in a directory named `venv/` in the project root, with the latter being preferred (and often supported as a default in project scripts).

## Python Packages and Dependencies

The internal project packages have several external dependencies.  Some are "standard" dependencies, while others are required for building package distribution files.  

Additionally, there are dependency relationships between several of the internal project packages.  As such, to develop (and especially to test) reliably, internal packages also need to be installed in the local Python environment.  

### Using `update_package.sh` for Dependencies and Internal Packages

For simplicity, the [scripts/update_package.sh](scripts/update_package.sh) Bash script can help with all of this automatically.  If not passed a specific package source directory, it will build and install all internally developed Python packages.  

This script also has options for first installing dependencies from the [requirements.txt](requirements.txt) file, either as an independent task or before proceeding to build and install the appropriate internal Python package(s).  

See its _help_/_usage_ message for more details.

## Docker Secrets Files

Several [Docker secrets](https://docs.docker.com/engine/swarm/secrets/) are used within DMOD, which require secrets files to be set up on the host.  These can be created manually, but it is recommended you allow the `./scripts/control_stack.sh` script to create them for you.  This happens as part of the `build` or `deploy` actions. Password-related secrets have randomly generated content; you can manually modify these after if desired.

Secret file locations are handled by the environment config variables listed below.  Note that you should ensure these files - especially those for passwords - are not committed to the repo.

> [!NOTE]
> The `docker/secrets/` directory is configured to be ignored by git and used in the config created by the [helper tool for environment configs](#environment-configuration-helper-script).  This is recommended location, unless you place your secret files outside the repo directory structure.

## Applying Swarm Constraint
Some services have placement constraints included in their service deployment config, which allow for control of which physical host(s) are suitable for such services.  Many of these constraints are fully configurable within the environment config, with these having reasonable defaults to ensure their use is (effectively) optional.

> [!IMPORTANT]
> If no node is found to satisfy a constraint for a service, the service will not start, though there is no obvious error produced.  It should be possible to update a node to satisfy the constraint without restarting the stack to get the service to start.

### Required Swarm Labels

Additionally, some constraints are hard-coded to check for certain labels associated with a node within Docker Swarm.  In such cases, labels must be added, and because of the nature of this, it must be done manually.

It is possible to later remove a label, add multiple labels to a single host, and/or add a single label to multiple hosts.

Labels can be added using the `docker node update command`:

```bash
docker node update --label-add "minio1=true" --label-add "object_store_proxy=true" <docker-node-id-or-name>
```

#### Labeling Nodes for Object Store

Several labels are required for the `object_store` stack:
- Suitable host(s) must be labeled to accept the minio proxy service with `object_store_proxy=true`
- Suitable host(s) must be labeled to accept the `minio1` service with `minio1=true`
- If utilized, suitable host(s) must be labeled to accept the `minio2` service with `minio2=true`

## Docker Images

DMOD deploys using several Docker stacks, and the service/worker containers within those stacks require custom Docker images.  These must be built before a deployment can be started.  The [`scripts/control_stack.sh`](./scripts/control_stack.sh) script has subcommands for performing these builds.

The following is usually enough to get started (note that order is important):

```
./scripts/control_stack.sh py-sources build push
./scripts/control_stack.sh main build push
```

## Object Store Setup

There are a few initialization steps necessary for the object store integration.  First, start the object store stack:

```bash
./scripts/control_stack.sh object_store start
```

Once confirmed with `docker service ls` that services have fully started, you will need to initialize the user and group used by DMOD.  A helper script handles this for you:

```bash
./scripts/minio_init.sh --create-admin-alias
```

## The Scheduler Service Resource Configuration
A special configuration file is needed by the scheduler that indicates the compute resources available for the deployment.  The file itself is named `resources.yaml` and must be located in the directory configured by `SCHEDULER_RESOURCE_DIR` in the environment config.

A helper script is available at `./scripts/create_resources_config.sh` that will create the file as needed for the environment config.  It does require arguments for the total CPUs and memory (in bytes) available to allocated to jobs, with the `--cpus` and `--memory` flags respectively.  E.g.:

```bash
# See './scripts/create_resources_config.sh --help' for more info

./scripts/create_resources_config.sh --cpus 12 --memory 8000000000
```

## The Scheduler Images and Domains Configuration
> [!IMPORTANT]
> Functionality is currently broken for features supported by this config, though it is still required. For now, just rely on the automated scripts to create a placeholder file for you.

A file must be supplied to the scheduler with details for pre-ngen NWM domains and the images to use for various jobs.  This is the `images_and_domains.yaml` file, located in the directory configured by `SCHEDULER_RESOURCE_DIR` in the environment config.

This file is automatically generated by the `./scripts/control_stack.sh` script, though specific deployments may need to manually modify it.

<!--- TODO: re-add this once such a readme exists!
See the [Docker usage README](./docker/README.md) for more information on Docker stacks, images, and building commands.
--->