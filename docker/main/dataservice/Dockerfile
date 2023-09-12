ARG docker_internal_registry
################################################################################################################
FROM ${docker_internal_registry}/dmod-py-sources:latest as sources

################################################################################################################
FROM rockylinux:8.5 as service

# Do this separately at the beginning to get some caching help
RUN dnf update -y && \
    dnf install -y python39 python39-pip git \
    && ln -s /usr/bin/pip3 /usr/bin/pip \
    && ln -s /usr/bin/python3 /usr/bin/python

ARG service_package_name
ARG service_package_constraint
WORKDIR /code
# Copy custom built packages from external sources image
COPY --from=sources /DIST /DIST

# Small possibility will find after testing that we'll need to 'dnf install -y` some of these dependencies:
#  gcc-c++ libffi-devel proj proj-devel gdal-devel openblas openblas-devel
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir aiohttp==3.8.1 \
    && pip install --no-cache-dir --find-links=/DIST "${service_package_name}${service_package_constraint}" \
    # TODO: this is a workaround, and may have side effects (transitive dependency issue with aiohttp and redis) \
    && pip install --no-cache-dir aiohttp==3.8.1 \
    && rm -rf /DIST

COPY entrypoint.sh entrypoint.sh

# TODO: when image tagging/versioning is improved, look at keeping this in a "debug" image only
# Copy this to have access to debugging pydevd egg
COPY --from=sources /dmod /dmod_src
RUN chmod u+x entrypoint.sh \
    && if [ -e /dmod_src/python/pydevd-pycharm.egg ]; then mv /dmod_src/python/pydevd-pycharm.egg /. ; fi \
    && rm -rf /dmod_src

ENTRYPOINT ["/code/entrypoint.sh"]
