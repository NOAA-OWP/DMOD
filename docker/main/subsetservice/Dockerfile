# problem using the current registry (127.0.0.1:5000), apparently due to the ':'
# which Docker thinks is an invalid --from value in the multi-stage copy step
ARG docker_internal_registry
FROM ${docker_internal_registry}/dmod-py-sources as sources

FROM rockylinux:8.5

# Do this separately at the beginning to get some caching help
RUN dnf update -y && \
    dnf install -y python39 python39-pip git \
    && ln -s /usr/bin/pip3 /usr/bin/pip \
    && ln -s /usr/bin/python3 /usr/bin/python

ARG comms_package_name
ARG modeldata_package_name
ARG subsetservice_package_name

WORKDIR /code

# Might need to make sure some of these are installed later via 'dnf install -y` (now that we've moved to Rocky Linux)
# git gcc gfortran python3 python3-dev py-pip build-base wget geos-dev gdal-dev freetype-dev libpng-dev openblas-dev proj proj-dev proj-util

# Copy custom built packages from external sources image
COPY --from=sources /DIST /DIST

COPY ./entrypoint.sh entrypoint.sh
# Install custom and generally available packages, starting with any custom from external source image
# Do these first packages separately first to work around some current issues (2/1/2022)
# TODO: fix root cause for problem this works around
RUN pip install --no-cache websockets MarkupSafe yarl wrapt \
    && pip install --no-cache --find-links=/DIST ${subsetservice_package_name} \
    # After eventually installing all custom packages like this, clean up ... \
    && rm -r /DIST

# TODO: when image tagging/versioning is improved, look at keeping this in a "debug" image only
# Copy this to have access to debugging pydevd egg
COPY --from=sources /dmod /dmod_src
RUN if [ -e /dmod_src/python/pydevd-pycharm.egg ]; then mv /dmod_src/python/pydevd-pycharm.egg /. ; fi \
    && rm -rf /dmod_src

ENTRYPOINT ["/code/entrypoint.sh"]
