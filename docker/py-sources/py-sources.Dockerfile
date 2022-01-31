################################################################################################################
################################################################################################################
##### Create base level intermediate build stage
FROM python:3.8-alpine as basis
ARG REQUIRE="gcc g++ musl-dev gdal-dev libffi-dev openssl-dev rust cargo git"
RUN apk update && apk upgrade && apk add --no-cache ${REQUIRE}
# Install a few requirements that are going to be expected first, since they take a very long time
# I.e., we prefer not to go through an hour of building/installing again whenever some other requirement changes
RUN mkdir /DIST \
    && if [ ! -d /CACHE ]; then mkdir /CACHE; fi \
    && pip install --upgrade pip \
    && pip wheel --cache-dir /CACHE --wheel-dir /DIST --prefer-binary pandas geopandas setuptools wheel cryptography numpy
# Copy project requirements file, which should have everything needed to build any package within project
COPY ./requirements.txt /dmod/requirements.txt
# Along with setup and wheel to build, install any remaining (see above) project pip dependencies for package building later
RUN pip wheel --cache-dir /CACHE --wheel-dir /DIST --prefer-binary -r /dmod/requirements.txt
# Needed for sourced functions used by build scripts in later stages
RUN mkdir -p /dmod/scripts/shared
COPY ./scripts/dist_package.sh /dmod/scripts
COPY ./scripts/shared /dmod/scripts/shared
# Copy python sources
COPY ./python /dmod/python
# Move to source dir
WORKDIR ./dmod

################################################################################################################

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
        [ -e python/services/${p}/setup.py ] && ./scripts/dist_package.sh --sys python/services/${p}  && mv python/services/${p}/dist/*.whl /DIST/. ; \
    done
################################################################################################################

################################################################################################################
################################################################################################################
#### Create final Docker build stage for desired image
FROM python:3.8-alpine
# Copy complete python source packages to location
COPY ./python /dmod/
# And for every built dist/wheel package copy wheel file into analogous location for this stage
COPY --from=lib_packages /DIST/* /DIST/
COPY --from=service_packages /DIST/* /DIST/
################################################################################################################
