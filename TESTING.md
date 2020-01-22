# Testing

## Conventions

Several conventions are followed for things related to testing.  These are sometimes to be consistent with external conventions and tools, such as `unittest`.  Other times they relate to something project-specific, like one of the testing scripts.

As such, if you know what you are doing, they aren't necessarily set in stone, but YMMV when violating these suggestions.

### Test Packages

For namespace packages, automated unit and integration test files live in a `test` package/directory under the parent namespace directory (i.e., `nwmaas/`).  This will be a sibling to the main package source directory. Something like:

    lib/
        access/
            nwmaas/
                access/
                test/

### Automated Test Files

* Automated tests are built using the `unittest` package
* Unit test files are named `test_*.py`
* Integration test files are named `it_*.py`
* Any once-pre-test setup and once-post-test teardown tasks for integration tests are in a `setup_it_env.sh` file ([see further explanation](#integration-test-environment-setupteardown))

#### Integration Test Environment Setup/Teardown

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

To facilitate this, `setup_it_env.sh` files can be created in a test package with `do_setup()` and `do_teardown()` function to execute these types of tasks.  The functions can then be sourced and run as needed by the [later-described `test_package.sh`](#test_packagesh).

## Project Scripts

There are useful scripts in `scripts/` made for facilitating automated unit and/or integration testing.

### `test_package.sh`

The `test_package.sh` allows for easily running all the tests for a supplied namespace package.  It provides options for running integration tests, one-time setup or teardown tasks needed for running a sporadic, potentially manual series of integration tests (useful for debugging integration test), and explicitly setting a virtual environment.  See the `-h` help output for more details.

E.g. to execute unit tests for the communication package, run (from the project root):

    ./scripts/test_package.sh lib/communication
    
### `run_tests.sh`

The `run_tests.sh` allows for running all unit tests or all integration tests for all of a configured group of supported packages, displaying either just a summary or more verbose output on test performance.  See the `-h` help option for more usage details.  

E.g. to run all unit tests on supported packages and display a summary:

    ./scripts/run_tests.sh 

