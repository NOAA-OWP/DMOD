##### Create base level intermediate build stage
FROM python:3.7-alpine as basis
# Needed for sourced functions used by build scripts in later stages
COPY ./scripts /nwm_service/scripts
# Copy python sources
COPY ./python /nwm_service/python
# Copy project requirements file, which should have everything needed to build any package within project
COPY ./requirements.txt /nwm_service/requirements.txt
# Move to source dir
WORKDIR ./nwm_service
# Along with setup and wheel to build, install all project pip dependencies for package building later
RUN mkdir /DIST && pip download --no-cache-dir --destination-directory /DIST -r /nwm_service/requirements.txt

##### Create intermediate Docker build stage for building wheel distributions for lib packages
FROM basis as lib_packages
ARG comms_package_name
ARG access_package_name
ARG externalrequests_package_name
ARG scheduler_package_name
RUN for p in communication access externalrequests scheduler; do \
        ./scripts/dist_package.sh --sys python/lib/${p} && mv python/lib/${p}/dist/*.whl /DIST/.; \
    done

##### Create intermediate Docker build stage for building wheel distributions for service packages
FROM basis as service_packages
ARG request_service_package_name
ARG scheduler_service_package_dist_name
# Set these expressly in the environment, since probably not sourced from env (not sure if still needed)
ENV PYTHON_PACKAGE_DIST_NAME_REQUEST_SERVICE=${request_service_package_name}
ENV PYTHON_PACKAGE_DIST_NAME_SCHEDULER_SERVICE=${scheduler_service_package_dist_name}
# Build service dist packages
RUN for p in requestservice schedulerservice; do \
        ./scripts/dist_package.sh --sys python/services/${p}  && mv python/services/${p}/dist/*.whl /DIST/. ; \
    done

#### Create final Docker build stage for desired image
FROM python:3.8-alpine
# Copy complete python source packages to location
COPY ./python ./gui /nwm_service/
# And for every built dist/wheel package copy wheel file into analogous location for this stage
COPY --from=lib_packages /DIST/* /DIST/
COPY --from=service_packages /DIST/* /DIST/