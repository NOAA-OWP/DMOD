# About

Herein is the source for a simple web based frontend based largely on existing code provided by Chris Tubbs.

Within _MaaS/cbv/EditView.py_ is a class named `PostFormRequestClient` that implements `MaasRequestClient` and serves as the client for communicating with the request service.  It is used by the `EditView` class, which currently is the main view for the webapp.

# Distribution Differences

The GUI source does not follow the same conventions as some other internal packages.  In particular, the project doesn't generate wheel files for distributing.  As such, it gets its own sub-directory immediately under _python/_, rather than being considered a *library* or *service* package.

Instead of dist files, the GUI stack build and deploy configuration will construct an image that the source appropriately copied into the image's filesystem.  It also has an entrypoint.sh script that executes the GUI appropriately.

