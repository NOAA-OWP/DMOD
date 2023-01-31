ARG docker_internal_registry
FROM ${docker_internal_registry}/dmod-py-deps:latest as basis
# Copy these needed for sourced functions used by build scripts in later stages
RUN mkdir -p /dmod/scripts/shared
COPY ./scripts/dist_package.sh /dmod/scripts
COPY ./scripts/shared /dmod/scripts/shared
# Copy python sources
COPY ./python /dmod/python
# Move to source dir
WORKDIR ./dmod

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for building wheel distributions for lib packages
FROM basis as lib_packages
ARG comms_package_name
ARG access_package_name
ARG externalrequests_package_name
ARG scheduler_package_name
# Set this so script below will not run logic that only applies to when in a full Git repo directory tree
ENV OUT_OF_GIT_REPO=true
RUN for p in `ls python/lib`; do \
        [ -e python/lib/${p}/setup.py ] && ./scripts/dist_package.sh --sys python/lib/${p} && mv python/lib/${p}/dist/*.whl /DIST/.; \
    done
################################################################################################################

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for building wheel distributions for service packages
FROM basis as service_packages
ARG request_service_package_name
ARG scheduler_service_package_dist_name
# Set these expressly in the environment, since probably not sourced from env (not sure if still needed)
ENV PYTHON_PACKAGE_DIST_NAME_REQUEST_SERVICE=${request_service_package_name}
ENV PYTHON_PACKAGE_DIST_NAME_SCHEDULER_SERVICE=${scheduler_service_package_dist_name}
# Set this so script below will not run logic that only applies to when in a full Git repo directory tree
ENV OUT_OF_GIT_REPO=true
# Build service dist packages
RUN for p in `ls python/services`; do \
        [ -e python/services/${p}/setup.py ] && ./scripts/dist_package.sh --sys python/services/${p} && mv python/services/${p}/dist/*.whl /DIST/. ; \
    done
################################################################################################################

################################################################################################################
################################################################################################################
#### Create final Docker build stage for desired image
FROM python:3.8-alpine3.15
WORKDIR /dmod
RUN apk update && apk upgrade && apk add --no-cache git
# Copy complete python source packages to location
COPY --from=basis /dmod /dmod
# And for every built dist/wheel package copy wheel file into analogous location for this stage
COPY --from=lib_packages /DIST/* /DIST/
COPY --from=lib_packages /CACHE/* /CACHE/
COPY --from=service_packages /DIST/* /DIST/
COPY --from=service_packages /CACHE/* /CACHE/
################################################################################################################
