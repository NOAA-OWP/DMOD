# Context

When DMOD Python package code changes, be it service or library package code, it is often necessary to test in the context of a running deployment.  The standard way to deploy code changes is to rebuild the `py-sources` stack images to build the packages, then one or more `main` stack service images, and then start or restart the `main` stack.

While in theory this is fine, practically it can be less than ideal.  This is especially true if something present in some of the related `main` stack service images cause the image rebuild time to take more than a few seconds.  This can happen, for example, if there needs to be an elongated dependency conflict resolution process for transitive external dependencies.  Regardless, this is especially frustrating if rapid adjustment and redeploying of changes is desired.

# A Faster Alternative

To support more rapid development environment change deployment, the
[docker-deploy.yml](../docker/main/docker-deploy.yml) has support added (but deactivated via comments) for use of a special `updated_packages` Docker volume.  The intent is for the commented out lines to be temporarily uncommented (but not committed as such) to allow services to mount this volume.  Supporting services have logic in their entrypoint scripts such that, when this is done, they will update packages appropriately on startup.

# How to Use

* Prepare [docker-deploy.yml](../docker/main/docker-deploy.yml)
  * Uncomment the `updated_packages` config under `volumes`
  * For each service of interest:
    * Uncomment the `volumes` config entry mounting the `updated_packages` volume
    * Uncomment the `environment` config entry that indicates where the volume is mounted in the container to the service's entrypoint script
    * Make sure `UPDATED_PACKAGES_CONTAINER_DIR` is set properly in your DMOD environment config (see the [example.env](../example.env) file for details)
* Use the helper script [prep_fast_dev_update.sh](../scripts/prep_fast_dev_update.sh) to build updated packages, create the Docker volume, copy the packages to the volume, and (if desired) automatically deploy them to services
* When done, re-comment the relevant lines in [docker-deploy.yml](../docker/main/docker-deploy.yml)
