# About
Image for creating container to serve as client-side for testing `request_handler` logic.

# TODO: Deprecated
This should be removed.  Replace by spinning up second container using same Docker image as server-side for `request_handler`, but override entry point with the following: 

`python tests.py`