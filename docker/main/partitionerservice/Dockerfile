ARG docker_internal_registry
# Making this an "empty" stage just so it can be copied-from in the next stage
FROM ${docker_internal_registry}/dmod-py-sources as sources

FROM rockylinux:8.5

# Do this separately at the beginning to get some caching help
RUN dnf update -y && \
    dnf install -y python39 python39-pip git \
    && ln -s /usr/bin/pip3 /usr/bin/pip \
    && ln -s /usr/bin/python3 /usr/bin/python

ARG partitioner_service_package_name
ARG partitioner_service_listener_port

# Small possibility will find after testing that we'll need to 'dnf install -y` some of these dependencies:
# libstdc++ openblas-devel proj-devel gdal-devel geos-devel

WORKDIR /code

# Copy custom built packages from previous stage FROM external sources image
COPY --from=sources /DIST /DIST

RUN pip install --upgrade pip \
    && pip install --no-cache --find-links=/DIST ${partitioner_service_package_name} \
    # After eventually installing all custom packages like this, clean up ... \
    && rm -r /DIST

EXPOSE ${partitioner_service_listener_port}

# TODO: when image tagging/versioning is improved, look at keeping this in a "debug" image only
# Copy this to have access to debugging pydevd egg
COPY --from=sources /dmod /dmod_src
RUN if [ -e /dmod_src/python/pydevd-pycharm.egg ]; then mv /dmod_src/python/pydevd-pycharm.egg /. ; fi \
    && rm -rf /dmod_src

COPY entrypoint.sh /code/entrypoint.sh

ENTRYPOINT [ "/code/entrypoint.sh" ]
