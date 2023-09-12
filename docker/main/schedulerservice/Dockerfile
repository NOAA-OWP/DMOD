# problem using the current registry (127.0.0.1:5000), apparently due to the ':'
# which Docker thinks is an invalid --from value in the multi-stage copy step
ARG docker_internal_registry
FROM ${docker_internal_registry}/dmod-py-sources:latest as sources

FROM rockylinux:8.5 as service

# Do this separately at the beginning to get some caching help
RUN dnf update -y && \
    dnf install -y python39 python39-pip git \
    && ln -s /usr/bin/pip3 /usr/bin/pip \
    && ln -s /usr/bin/python3 /usr/bin/python

# Not yet 100% sure we don't need more of these commented-out things installed, but the service does start without them
# # libffi-dev libstdc++ geos-devel openblas-devel proj proj-devel gdal-dev

ARG comms_package_name
ARG scheduler_package_dist_name
ARG scheduler_service_package_dist_name
ARG scheduler_service_package_version_constraint

WORKDIR /code

# Copy custom built packages from external sources image
COPY --from=sources /DIST /DIST

RUN pip install --no-cache-dir --upgrade pip \
    # Install service package, which should be available in /DIST \
    && pip install --no-cache-dir --find-links=/DIST "${scheduler_service_package_dist_name}${scheduler_service_package_version_constraint}" \
    # TODO: this is a workaround, and may have side effects (transitive dependency issue with aiohttp and redis) \
    && pip install --no-cache-dir aiohttp==3.8.1 \
    # After installing everything needed from /DIST, clean up ... \
    && rm -r /DIST \
    && mkdir -p ~/.ssh \
    && printf "Host *\n        ServerAliveInterval 300\n        ServerAliveCountMax 2\n" >> ~/.ssh/config

COPY ./entrypoint.sh entrypoint.sh

# TODO: when image tagging/versioning is improved, look at keeping this in a "debug" image only
# Copy this to have access to debugging pydevd egg
COPY --from=sources /dmod /dmod_src
RUN if [ -e /dmod_src/python/pydevd-pycharm.egg ]; then mv /dmod_src/python/pydevd-pycharm.egg /. ; fi \
    && rm -rf /dmod_src

ENTRYPOINT ["/code/entrypoint.sh"]
