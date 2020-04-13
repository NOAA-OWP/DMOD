# Installation instructions

Detailed instructions on how to install, configure, and get the project running.


# TL;DR

- Be familiar with [usage dependencies](#usage-dependencies) and [development dependencies](#development-dependencies), as well as the [caveat](#dependency-caveat) about strictness
- Perform [general project setup](#general-setup) steps
    - Create a [customized `.env` config file](#create-customized-env), based on the provided [example](example.env)
    - [Create an `ssl/` directory and SSL certificates](#local-ssl-certs)
- Perform [Python development setup](#python-development-setup) steps
    - Ensure Python is installed
    - [Create dedicated Python virtual environment for development](#using-a-virtual-environment) (highly recommended, though not strictly required)
    - Install necessary [external and internal packages](#python-packages-and-dependencies) into Python environment, typically using the [provided helper script](#using-update_packagesh-for-dependencies-and-internal-packages)

# Dependencies

- [Usage Dependencies](#usage-dependencies)
- [Development Dependencies](#development-dependencies)
- [Dependency Caveat](#dependency-caveat)

## Usage Dependencies

- Bash shell
- Docker Swarm
- OpenSSL command line tool (to generate self-signed SSL certificates)

## Development Dependencies

- All above listed [Usage Dependencies](#usage-dependencies)
- Python 3.6+ 
- Python package as defined in [requirements.txt](requirements.txt)

## Dependency Caveat
The usage of the term "dependency" in this doc is not necessarily in the strictest possible sense.  I.e., it may be possible to work without something listed here as a dependency, by performing some task(s) manually or through use of various forms of hackery.  A known example of this is the OpenSSL CLI dependencies.  Project tools require this to generate SSL certs, but you can work around this if you are otherwise able to obtain certs and manually put them where they need to be.

However, it is highly recommended the listed items be assumed as dependencies in most cases.  Once you get comfortable enough with the project that you are able to work around using a stated dependency, it is probably time to think about formally contributing what you are doing to the project.

# General Setup

This is what is required for general use of the DMoD services on a single system or collection of systems.

- Ensure [usage dependencies](#usage-dependencies) are installed 
- Create a [customized `.env` config file](#create-customized-env), based on the provided [example](example.env)
- [Create an `ssl/` directory and SSL certificates](#local-ssl-certs)

## Create customized `.env`

A custom `.env` file needs to be created in the project root to configure various aspects and setttings in the development environment.  

While the [up_stack.sh](up_stack.sh) script will create a default version automatically, it is also possible to copy the [example.env](example.env) file and edit it manually.  The template file contains comments explaining what the properties are and how they are used.
    
## Local SSL Certs

The project by default expects to find an `ssl/` directory in the project root as the based directory for organizing needed certificates.  This will have to be created manually, as it is configured to be ignored by Git and not included in the repo.

When setting this up, start by creating `ssl/`, and then create the `requestservice/`, `scheduler/` and `local/` subdirectories.  Place within these directories the certificate keypair files used by these services.  Note that the `local/` directory is primarily used in testing.  

If you do not already have certificates, you can easily generate some using the provided [gen_cert.sh](scripts/gen_cert.sh) script under `scripts/`.  However, the script depends on the `openssl` utility being installed.  Steps for performing that are beyond the scope of this.

# Python Development Setup

- Ensure Python is installed
- [Create dedicated Python virtual environment for development](#using-a-virtual-environment) (highly recommended, though not strictly required)
- Install necessary [external and internal packages](#python-packages-and-dependencies) into Python environment, typically using the [provided helper script](#using-update_packagesh-for-dependencies-and-internal-packages)

## Using a Virtual Environment

It is recommended you use a Python virtual environment if you intend to do development on the Python source code used by the project.  This is not an absolute requirement, but typically is appropriate. 

The project is tested to work with environments created by the `venv` module.  Additionally, it is recommended the directory be either located outside the project root or in a directory named `venv/` in the project root, with the latter being preferred.

## Python Packages and Dependencies

The internal project packages have several external dependencies, both directly and to perform the tasks necessary to build their distribution files.  Additionally, there are dependency relationships between several of the internal project packages.  As such, to develop (and especially to test) reliably, both external dependencies and the internal packages need to be installed in your local Python environment.  

### Using `update_package.sh` for Dependencies and Internal Packages

For simplicity, the [update_package.sh](scripts/update_package.sh) Bash script under `scripts/` can help with all of this automatically.  If not passed a specific package source directory, it will build and install all internally developed packages.  It also has options for first installing dependencies from the [requirements.txt](requirements.txt) file, either as an independent task or before proceeding to build and install the appropriate internal Python package(s).  See it help/usage message for details.