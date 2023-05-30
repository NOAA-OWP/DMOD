# Installation instructions

Detailed instructions on how to install, configure, and get the project running.

# TL;DR

- Install project [dependencies](doc/DEPENDENCIES.md)
  - Optionally, setup and use a [dedicated Python virtual environment](#using-a-virtual-environment) (highly recommended)
- Create a [customized local environment config](#local-environment-configuration)
- Set up the [required SSL certificates](#local-ssl-certs)
- Build and install necessary [internal Python packages](#python-packages-and-dependencies) into Python environment, typically using the [provided helper script](#using-update_packagesh-for-dependencies-and-internal-packages)
- [Build Docker images](#docker-images)

## Local Environment Configuration

Each local deployment and/or development environment requires its own configuration be set up in order to function properly.  This is currently done via a local environment file.  

Because of its custom nature and potentially sensitive contents, local environment configs should never be committed to the Git repo.  As such, one must be custom built for a given environment.

### File Name and Path

The general recommendation is to name this file `.env` and place it the project root on development systems.  This is the expected default for many DMOD management script and tools.  The Git repo is also configured to ignore this path.

However, most DMOD management tools support an optional parameter for setting a custom path to an environment config, so a file can be named or located elsewhere if needed.

### Creating

The file can be created by copying the [example.env](example.env) template file committed to the repo and editing it as needed.  This template file contains comments explaining what the properties are and how they are used.
    
## Local SSL Certs

### About Service SSL Directories
Several service components of DMOD require self-signed SSL certificates to secure incoming connections.  DMOD expects a parent SSL directory containing several service-specific sub-directories.  Assuming the top-level directory is named `ssl/`, the structure is as follows:

```
ssl
├── dataservice
│    ├── certificate.pem
│    └── privkey.pem
├── local
│    ├── certificate.pem
│    └── privkey.pem
├── partitionerservice
│    ├── certificate.pem
│    └── privkey.pem
├── requestservice
│    ├── certificate.pem
│    └── privkey.pem
└── scheduler
     ├── certificate.pem
     └── privkey.pem
```

Note that the `local/` directory is primarily for tests, rather than a service.

As illustrated, each service sub-directory must then contain two files:

* _certificate.pem_ 
  * the actual SSL certificate 
* _privkey.pem_ 
  * the private key used to create the certificate


### Setup Process

* Setup the SSL directory structure
  * [Option 1: create the default SSL directories under `<project_root>/ssl/`](#option-1-create-default-ssl-directories-under-project_rootssl), or
  * [Option 2: create custom SSL directories](#option-2-user-defined-ssl-directories)
* Place valid _certificate.pem_ and _privkey.pem_ file pairs in each service sub-directory
  * If necessary, [create these files using the provided helper script](#creating-self-signed-certificates) 
* Mirror this structure appropriately across all physical hosts for the deployment (Work is planned to implement managing via Docker Secrets instead)

#### Option 1: Create Default SSL Directories Under `<project_root>/ssl/`
DMOD is designed to work with a default SSL directory of `ssl/`, relative to the repo project root directory.  However, the directory structure itself must be created manually.

Certificates should never be committed to the repo, so the default path `ssl/` is ignored by Git.  It therefore does not exist in the repo, and so must be created manually separately from the clone/checkout process.

#### Option 2: User-Defined SSL Directories

The path of the parent SSL directory is configurable via the [.env file](#create-customized-env), via the `DMOD_SSL_DIR` variable (see comments in your `.env` and/or the [example template](example.env)).  The directory must be usable for a Docker host bind mount; e.g., local NFS mounts may have issues.  (Work is pending on managing via Docker Secrets instead.)

#### Creating Self-Signed Certificates
Self-signed certificates and keys like this can be created using the included [gen_cert.sh](scripts/gen_cert.sh) script under `scripts/`.

# Python Development

## Using a Virtual Environment

It is recommended that contributors use a Python virtual environment if they intend to do development on the Python source code used by the project.  This is not an absolute requirement, but typically is appropriate. 

The project is tested to work with environments created by the `venv` module.  Additionally, it is recommended the directory be either located outside the project root or in a directory named `venv/` in the project root, with the latter being preferred (and often supported as a default in project scripts).

## Python Packages and Dependencies

The internal project packages have several external dependencies.  Some are "standard" dependencies, while others are required for building package distribution files.  

Additionally, there are dependency relationships between several of the internal project packages.  As such, to develop (and especially to test) reliably, internal packages also need to be installed in the local Python environment.  

### Using `update_package.sh` for Dependencies and Internal Packages

For simplicity, the [scripts/update_package.sh](scripts/update_package.sh) Bash script can help with all of this automatically.  If not passed a specific package source directory, it will build and install all internally developed Python packages.  

This script also has options for first installing dependencies from the [requirements.txt](requirements.txt) file, either as an independent task or before proceeding to build and install the appropriate internal Python package(s).  

See its _help_/_usage_ message for more details.

## Docker Images

DMOD deploys using several Docker stacks, with many of the service/worker containers within those stacks requiring custom Docker images.  These must be built before a deployment can be started.   The [`scripts/control_stack.sh`](./scripts/control_stack.sh) script can help with this

The following is usually enough to get started (note that order is important):

```
./scripts/control_stack.sh py-sources build
./scripts/control_stack.sh main build
```

See the [Docker usage README](./docker/README.md) for more information on Docker stacks, images, and building commands.