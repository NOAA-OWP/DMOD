# Dependencies

The DMOD project has two related sets of dependencies: 

* those needed to run and use a DMOD deployment
* those needed for development work

## Usage Dependencies

| Dependency              | Constraints         |                                                                  Notes                                                                 |
|-------------------------|:--------------------|:--------------------------------------------------------------------------------------------------------------------------------------:|
| Docker Engine           | \>=20.10.16         |                      Docker Swarm support required (i.e., alternatives without this, like Podman, are insufficient)                    |
| Docker Compose          | \>=2.0.x            |               [See issue #133](https://github.com/NOAA-OWP/DMOD/issues/133); _deployx_ plugin now required as noted below              |
| _deployx_ Docker plugin | \>=0.0.1            | Available [here](https://github.com/aaraney/deployx).  Results in some transitive dependencies not explicitly enumerated here (e.g., Go) |
| Bash                    | \>=3.2.57           |                                                                                                                                        |
| OpenSSL / LibreSSL      | \>=3.0.0 / \>=2.8.3 |                                                                                                                                        |
| MinIO CLI client        |  |                                                                                                                                        |

## Development Dependencies
| Dependency                                | Constraints                                 |                                 Notes                                  |
|-------------------------------------------|:--------------------------------------------|:----------------------------------------------------------------------:|
| [Usage Dependencies](#usage-dependencies) | Same as above                               |                                                                        |
| Python                                    | \>=3.8.x                                    |                                                                        |
| Python Pip                                | Analogous to installed Python version       |                                                                      |
| Python Development Headers/Libs           | Analogous to installed Python version       | Required for building certain Python dependency wheels; e.g., *pandas*                                                                       |
| C++ Compiler                              |        | Required for building certain Python dependency wheels; e.g., *pandas* |
| Python Packages                           | See [requirements.txt](../requirements.txt) |           Recommend installing in Python virtual environment           |

## Dependency Caveats
The strictness of these dependencies can vary in different situations, in a way that is hard to define concisely.  E.g., one could probably avoid installing Bash by manually performing all the tasks handled by Bash scripts [^1].  Also, OpenSSL is not needed (locally) if all required SSL certificates can be provided from elsewhere.  And somewhat related:  multi-node deployments probably don't need ***all*** dependencies on the non-primary node(s).

As a general rule, however, it is highly recommended to begin by installing all documented dependencies, until a user understands where and why any exception applies.  

[^1]: Or, even better, by writing other automation tools, which could then be contributed :-)