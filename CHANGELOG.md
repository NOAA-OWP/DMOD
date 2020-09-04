All notable changes to this project will be documented in this file.
We follow the [Semantic Versioning 2.0.0](http://semver.org/) format.

Note that this project has developed a set of libraries to support the
services that comprise the DMOD infrastructure.  With each project changelog,
library versions supporting the project will be documented with the
corresponding versions used for release.

## 0.1.0 - 2020-03-30
Public code release.

### Added

Services
Moved to dmod namespace.
* monitorservice
* requestservice
* schedulerservice

Library
Moved to dmod namespace, reset all library versions for new namespace.
* access 0.1.0
* communication 0.1.0
* externalrequests 0.1.0
* monitor 0.1.0
* redis 0.1.0
* scheduler 0.1.0

Docker
* dev_registry_stack
  - An ad-hoc docker registry which can be used in development
* main
  Contains the main docker configurations/files for the core services
  - base
  - monitorservice
  - myredis
  - nwm
  - requestservices
  - schedulerservice

* nwm_gui
  - A DMoD client web interface
* py-sources
  - Intermediate build source for the python sources in DMOD/PYTHON

Scripts
* secrets
  - Initial git secrets setup and provider
* shared
* Testing and utility scripts

### Deprecated

- Nothing

### Removed

- Nothing

### Fixed

- Nothing.
