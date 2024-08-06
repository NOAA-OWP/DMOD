ARG docker_internal_registry
FROM rockylinux:8.5 as deps

# Do this separately at the beginning to get some caching help
RUN dnf update -y && \
    dnf install -y python39 python39-pip git \
    && ln -s /usr/bin/pip3 /usr/bin/pip \
    && ln -s /usr/bin/python3 /usr/bin/python

ARG REQUIRE="python39 python39-devel python39-pip python3-pyproj gcc gcc-c++ gdal-devel libffi-devel openssl-devel rust cargo git proj proj-devel openblas openblas-devel lapack-devel geos-devel"

# Copy these needed for sourced functions used by build scripts in later stages
RUN dnf update -y \
    && dnf install -y 'dnf-command(config-manager)' \
    && dnf config-manager --set-enabled powertools \
    && dnf install -y epel-release \
    && dnf install -y ${REQUIRE} \
    && dnf clean all \
    && mkdir -p /dmod/scripts/shared \
    && pip install wheel
RUN mkdir /DIST
################################################################################################################
################################################################################################################
FROM deps as basis
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
        [ -e python/lib/${p}/pyproject.toml ] && ./scripts/dist_package.sh --sys python/lib/${p} && mv python/lib/${p}/dist/*.whl /DIST/.; \
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
        [ -e python/services/${p}/pyproject.toml ] && ./scripts/dist_package.sh --sys python/services/${p} && mv python/services/${p}/dist/*.whl /DIST/. ; \
    done
################################################################################################################

################################################################################################################
################################################################################################################
#### Create final Docker build stage for desired image
FROM deps
WORKDIR /dmod
RUN dnf install -y git
# Copy complete python source packages to location
COPY --from=basis /dmod /dmod
# And for every built dist/wheel package copy wheel file into analogous location for this stage
COPY --from=lib_packages /DIST/* /DIST/
COPY --from=service_packages /DIST/* /DIST/
################################################################################################################
