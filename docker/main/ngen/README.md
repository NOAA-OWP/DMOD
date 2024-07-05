# About

<b style="color: red">TODO:</b>More details about the image.

<b style="color: red">TODO:</b>Once implemented, details about available image variants.

<b style="color: red">TODO:</b>Once implemented, details about extending the image with additional modules.

# Image `/dmod/` Directory

## TL;DR - Directories for Configs

Several important pieces details if manually constructing configurations to upload into DMOD datasets:
* Compiled BMI module libraries will be in `/dmod/shared_libs/`
* Data used during job execution (e.g., forcings, configs) will (or at least appear) under `/dmod/datasets/`
  * Paths descend first by data type, then by dataset name
  * E.g., `/dmod/datasets/config/vpu-01-bmi-config-dataset-01/NoahOWP_cat-9999.namelist`
  * E.g., `/dmod/datasets/forcing/vpu-01-forcings-dataset-01/cat-1000.csv` 

## Directory Structure Details

Several important directories exist in the worker images' file system under the `/dmod/` directory, which are important to the operation of job worker containers.

## Static Directories

Several important DMOD-specific directories in the worker images are static.  They contain things either created or copied in during the image build.  These are standard/general things, available in advance, that need to be in fixed, well-defined locations.  Examples are the ngen executables, Python packages, and compiled BMI modules.

### `/dmod/bin/`
* Directory containing custom executables and scripts
* Location for parallel and serial ngen executables, plus the `ngen` symlink that points to one of them (dependent on build config, but parallel by default)
* Path appended to `PATH` in environment

### `/dmod/bmi_module_data/`
* Directory containing any necessary generic per-BMI-module data files
  * `/dmod/bmi_module_data/noah_owp/parameters/`
    * Nested directory containing parameters files for Noah-OWP-Modular
  * `/dmod/bmi_module_data/lgar-c/data/data/`
    * Nested directory for generic LGAR data files
      
### `/dmod/shared_libs/`
* Directories containing libraries built during intermediate steps of the image building process that will be needed for worker container execution
* E.g., Compiled BMI module shared libraries, like `libcfebmi.so` for CFE
* Path is appended to `LD_LIBRARY_PATH`

### `/dmod/venv/`
* Directory for Python virtual environment loaded by worker for execution

## Dynamic Directories

Others important DMOD-specific directories in the worker images are dynamic.  There is a higher level baseline directory structure that is created by the image build, but the nested contents, which are what is most important to job execution, is put into place when the job worker container is created.  Examples of this are configs and forcings.

### `/dmod/datasets/`
* This contains the paths from which jobs should read their necessary data, and which config files should reference
* Contains subdirectories for different dataset types
  * `config`, `forcing`, `hydrofabric`, `observation`, `output` (e.g., `/dmod/datasets/forcing/`)
* Each subdirectory may contain further "subdirectories" (really symlinks) containing different data needed for the current job
  * E.g., `/dmod/datasets/config/vpu-01-bmi-config-dataset-01/`
    * Has data from `vpu-01-bmi-config-dataset-01` dataset
* Data subdirectories are actually symlinks to an analogous mounted path for either a [cluster volume](#dmodcluster_volumes) or [local volume](#dmodlocal_volumes)
  * If a dataset can be mounted as a cluster volume and used directly by the job without local copying, the symlink will be to an analogous cluster volume
    * e.g., `/dmod/datasets/config/real-cfg-ds-01/ -> /dmod/cluster_volumes/config/real-cfg-ds-01/` 
  * If data from a dataset needs to be local or preprocessed in some way by the worker before use, it will be prepared in a local volume, and a symlink here will point to that
    * e.g., `/dmod/datasets/config/vpu-01-bmi-config-dataset-01/ -> /dmod/local_volumes/config/vpu-01-bmi-config-dataset-01/`


### `/dmod/cluster_volumes/`
* First level subdirectories correspond to DMOD dataset types, as with `/dmod/datasets/`
  * e.g., `/dmod/cluster_volumes/config/`
* Second-level subdirectories are mounted Docker cluster volumes that are, in some way or another, synced across all physical nodes of the deployment
  * e.g., `/dmod/cluster_volumes/config/vpu-01-bmi-config-dataset-01/`
* Automatic synchronization at the DMOD deployment level
  * All workers for a job see exactly the same set of mounted volumes here
  * All workers on all physical nodes see the same contents in each mounted volume directory
  * Writes done on any worker to a file under a volume subdirectory are seen (essentially) immediately by workers on **all** physical nodes
* Common scenario (typical case at the time of this writing) for these are DMOD dataset volumes
  * A dataset is directly mounted as Docker volume via some specialized storage driver (e.g., `s3fs`)
  * The contents of the dataset can then be interacted with by the worker as if they were a regular file system (even if they aren't)
  * The mount directory name matches the DMOD dataset name
    * E.g., the `vpu-01-bmi-config-dataset-01` dataset would be at `/dmod/cluster_volumes/config/vpu-01-bmi-config-dataset-01/`

*** TODO: set up to link or do pre-processing/extraction/etc. as needed on startup ***
*** TODO: have indication that  be that there exists a directory already for the dataset under `/dmod/datasets/`
TODO: have this be for local Docker volumes that are just on individual hosts that we want to keep synced

### `/dmod/local_volumes/`
* First level subdirectories correspond to DMOD dataset types, as with `/dmod/datasets/`
  * e.g., `/dmod/local_volumes/config/`
* Second-level subdirectories are mounted Docker local volumes
  * e.g., `/dmod/local_volumes/config/vpu-01-bmi-config-dataset-01/`
* These local volumes are job-wide but host-specific
  * All workers for a job see exactly the same set of mounted volumes here
  * All workers on the same physical nodes are using the same local volume on that physical host
  * Workers on different physical nodes are using different volumes
  * This means some coordinated synchronization needs to be performed by a subset of worker
* The use case is for any data that needs to be local on the container/host (generally for performance reasons) to be copied/extracted to a subdirectory here, typically from an analogous subdirectory under `/dmod/cluster_volumes/`
  * This at least reduces copying somewhat by allowing workers on same node to share the same local volume

TODO: make scheduler create these per dataset on the fly at job time and mount them in (and have something to clean them up, but maybe not right away)
TODO: make one worker per physical host extract data when needed from archives in analogous cluster volumes
  