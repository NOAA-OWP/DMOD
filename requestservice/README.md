# About
Python package, Docker image file, and associated other files for external request handling logic for NWM MAAS.

# Structure
Structure has been modified from original to have inner duplicate directory in order to comply with general Python packaging structure.  This facilitates executing tests in a variety of different scenarios, including running integration tests on a local machine using the included test script and/or running unit tests directly within an IDE.

# Client-Side Testing
The primary Docker image can be used to run both the server side and a prepared client-side for basic integration testing.  To run the client-side, override the default entrypoint with:

`python tests.py` 