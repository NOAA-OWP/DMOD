# Subsetting CLI

The DMOD _subsetservice_ package module has several options available that allow it to run command line operations rather than starting the main API service.  This makes the package potentially useful outside the main DMOD MaaS environment. The following operations are supported:

* Creating a basic subset from a provided collection of catchments
* Creating a subset starting from a collection of catchments and proceeding upstream from each
* Subdividing GeoJSON hydrofabric files according to a partitioning configuration

#### Note: Limited Technical Details
The descriptions below make minimal assumptions about technical knowledge of related items, but they also provide limited technical detail.  This is intended as a quick and dirty guide to get up and running using this tool.  Feel free to adapt some of the steps appropriately where comfortable doing so.

## Running in the CLI

After it is [installed](#installing-_dmod-subsetservice_-in-a-virtual-environment), to use the subsetservice on the command line, make sure you are in the Python environment where it is installed.  I.e., if this is a virtual environment as described below, run:

`source venv/bin/activate`

Then, call the module using Python's `-m` flag:

`python -m dmod.subsetservice <options>`

To see the help message that describes what options are available to trigger certain operations, what parameters need to be provided for those, etc.:

`python -m dmod.subsetservice --help`

The options to focus on are for CLI usage (at the time of this writing) are:
* `--subset`
* `--upstream`
* `--partition-file`

The help details on those in particular should be reviewed, but keep in mind several of the other arguments are either needed to make those work or are useful to those operations.

Once you are done using the tool, if you want/need to exit a virtual environment, run:

`deactivate`

## Installing _dmod-subsetservice_ in a Virtual Environment

Before it can be used as described here, the _dmod-subsetservice_ package must be made available, along with its dependencies.  While there are several ways to do this, the simplest way is to create a virtual Python environment with _venv_ and use provided DMOD scripts to install things there.  The steps for that are listed below.  More detail on how the `update_package.sh` script works can be found by using its `--help` flag.

```
cd <dmod_project_dir>       # replace with appropriate local directory
python -m venv venv         # or 'python3' if appropriate
source venv/bin/activate    # enter the venv in this terminal
pip install --upgrade pip
pip install -r requirements.txt
./scripts/update_package.sh python/lib/communication
./scripts/update_package.sh python/lib/modeldata
./scripts/update_package.sh python/services/subsetservice
deactivate                  # exit the venv in this terminal
```

### Updating Later
If DMOD updates are ever made or pulled for these packages, just run the same steps from installign, except without the `python -m venv venv` command.  This will ensure the local virtual environment is appropriately updated.

### Caveats

* At this time, only **Mac** and **Linux** systems have been tested with these directions and the helper scripts.
* Python 3.6.x or later is required.  Use `python --version` to confirm.  Also, systems with multiple versions may require using the `python3` command instead of `python` to access version 3.x.
