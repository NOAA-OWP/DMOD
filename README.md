# Distributed Model on Demand

DMOD is a utility to facilitate running scientific models and other similar HPC application tasks.  Its primary purpose is to automate both the management of the necessary compute infrastructure and the performance of variety of execution workflows (e.g., a simple model test execution, evaluating a specific model configuration, etc.).  It also provides other tools for making certain model development and experiment tasks easier.

As of summer 2022, the project is in an early Alpha stage. Infrastructure and workflows have been initially developed with the [OWP Next Generation Water Resources Modeling Framework](https://github.com/NOAA-OWP/ngen) in mind, though the intent is to work toward a generalized design.

[//]: # (TODO: create sections and/or dedicated documents for these items)
[//]: # (- Architecture Overview)
[//]: # (- Services and Stacks)
[//]: # (- Code Organization)
[//]: # (- Workflows)
[//]: # (- Technology Stack)

[//]: # (**System Overview**)
[//]: # (![](https://raw.githubusercontent.com/noaa-owp/DMOD/master/doc/DMOD_system_overview.png\))


## Dependencies
The primary dependencies for this project are Docker, Python, and some specific Python packages.

More detailed information can be found on the [Dependencies](doc/DEPENDENCIES.md) page.

## Installation

The basic process is:
- Install project [dependencies](doc/DEPENDENCIES.md)
  - Optionally, setup and use a [dedicated Python virtual environment](INSTALL.md#using-a-virtual-environment) (highly recommended)
- Create a [customized local environment config](INSTALL.md#local-environment-configuration)
- Set up the [required SSL certificates](INSTALL.md#local-ssl-certs)
- Build and install necessary [internal Python packages](INSTALL.md#python-packages-and-dependencies) into Python environment, typically using the [provided helper script](#using-update_packagesh-for-dependencies-and-internal-packages)
- [Build Docker images](INSTALL.md#docker-images)

See the [INSTALL](INSTALL.md) document for more information.

[//]: # (TODO: add this section, and probably a dedicated document)
[//]: # (## Configuration)

[//]: # (TODO: add this section, and also a dedicated document)
[//]: # (## Usage)

[//]: # (TODO: add this section, and also a dedicated document)
[//]: # (## Testing)


[//]: # (TODO: add this section, and probably a dedicated document)
[//]: # (## Getting help)

[//]: # (Instruct users how to get help with this software; this might include links to an issue tracker, wiki, mailing list, etc.)

[//]: # (**Example**)

[//]: # (If you have questions, concerns, bug reports, etc, please file an issue in this repository's Issue Tracker.)

## Getting involved
See the [CONTRIBUTING](CONTRIBUTING.md) document for details.


----

## Open source licensing info
1. [TERMS](TERMS.md)
2. [LICENSE](LICENSE)


----

## Credits and references

Inspired by [WALKOFF](https://github.com/nsacyber/WALKOFF)
