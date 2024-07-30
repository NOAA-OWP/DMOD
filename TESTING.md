# Testing

- [TL;DR](#tldr)
- [Python Automated Testing](#python-automated-testing)
    - [Testing Prerequisites](#testing-prerequisites)
    - [Test Files and Filenames](#test-files-and-filenames)
    - [Test Sources Directories](#test-sources-directories)
    - [Automated Integration Testing Environment Services Setup/Teardown](#automated-integration-testing-environment-services-setupteardown)
    - [Testing Helper Scripts](#testing-helper-scripts)

# TL;DR

- Prepare environment for Python testing
    - Perform all [general setup](INSTALL.md#general-setup) and [Python development setup](INSTALL.md#python-development-setup) steps
    - Setup/verify global `.test_env` file, and optionally setup package-specific files
- Use the `test_package.sh` to run unit and/or integration tests for a specific internal Python package
- Use the `run_tests.sh` to run unit or integration tests for all internal packages

# Python Automated Testing

Python packages have automated tests written using the `unittest` Python package.  These include both unit and integration tests.

- [Testing Prerequisites](#testing-prerequisites)
- [Test Files and Filenames](#test-files-and-filenames)
- [Test Sources Directories](#test-sources-directories)
- [Automated Integration Testing Environment Services Setup/Teardown](#automated-integration-testing-environment-services-setupteardown)
- [Testing Helper Scripts](#testing-helper-scripts)

## Testing Prerequisites

- Perform all [general setup](INSTALL.md#general-setup) and [Python development setup](INSTALL.md#python-development-setup) steps
- Setup/verify [global `.test_env` file](#configuring-environment-test-settings), and optionally setup package-specific files

### Configuring Environment Test Settings

The project's testing helper scripts and some project integration tests expect and require a valid `.test_env` file to be present in the project root.  This file is used to configure certain settings in the testing environment that are better left outside the Git repo.

The [test_package.sh](scripts/test_package.sh) script will automatically create this global config file if it does not already exist, using either reasonable or randomly generated values, depending on the property. Since this script is used by the [run_tests.sh](scripts/run_tests.sh) script, the latter will also automatically generate the file.  There is also a template file [example_test_env](example_test_env) that explains what must be set.

Additionally, it is possible to optionally create package-specific `.test_env` file within the `test/` source directory of the package.  Any values in such files will override global settings for that package.

## Test Files and Filenames

* Automated tests are built using the `unittest` Python package
* Unit test files have names matching the pattern `test_*.py`
* Integration test files have names matching the pattern `it_*.py`
* For integration tests, any service setup and/or teardown tasks that should happen once per group of tests (as opposed to once per test function) are defined in a `setup_it_env.sh` file for the package ([see further explanation](#integration-test-environment-setupteardown))

## Test Sources Directories

For namespace packages, automated unit and integration test files live in a `test` sub-package/directory under the parent namespace directory (i.e., `dmod/`).  This will be a sibling to the main package source directory. Something like:

    python/
        lib/
            access/
                dmod/
                    access/
                    test/

## Automated Integration Testing Environment Services Setup/Teardown

There can often be test environment management tasks for integration testing that don't need to (or even that expressly should not) follow the typical "setup, exec test method, teardown" convention used in unit testing. An example could be setup/teardown of a Redis instance in a testing environment.  It would likely be excessive to follow the typical unit test convention:

* setup up _Redis instance 1_
* run `integration_test_method_1()`
* teardown _Redis instance 1_
* setup up _Redis instance 2_
* run `integration_test_method_2()`
* teardown _Redis instance 2_
* etc.

In many cases, a better option would be just setup a Redis instance once, run any desired tests, and tear it down once at the end:

* setup up _Redis instance 1_
* run `integration_test_method_1()`
* run `integration_test_method_2()`
* etc.
* teardown _Redis instance 1_

To facilitate this, `setup_it_env.sh` files can be created in a test package with `do_setup()` and `do_teardown()` function to execute these types of tasks.  The functions can then be sourced and run as needed by the [later-described `test_package.sh`](#test_packagesh), and then in turn by [run_tests.sh](#run_testssh).


## Testing Helper Scripts

There are useful scripts in `scripts/` made for facilitating automated Python unit and/or integration testing.

### `test_package.sh`

The `test_package.sh` allows for easily running all the tests for a supplied namespace package.  It provides options for running integration tests, one-time setup or teardown tasks needed for running a sporadic, potentially manual series of integration tests (useful for debugging integration test), and explicitly setting a virtual environment.  See the `-h` help output for more details.

E.g. to execute unit tests for the communication package, run (from the project root):

    ./scripts/test_package.sh lib/communication

### `run_tests.sh`

The `run_tests.sh` allows for running all unit tests or all integration tests for all of a configured group of supported packages, displaying either just a summary or more verbose output on test performance.  See the `-h` help option for more usage details.

E.g. to run all unit tests on supported packages and display a summary:

    ./scripts/run_tests.sh
