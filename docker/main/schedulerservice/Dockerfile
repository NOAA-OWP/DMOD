# problem using the current registry (127.0.0.1:5000), apparently due to the ':'
# which Docker thinks is an invalid --from value in the multi-stage copy step
ARG docker_internal_registry
FROM ${docker_internal_registry}/dmod-py-sources as sources

FROM python:3.8-alpine3.15
ARG comms_package_name
ARG scheduler_package_dist_name
ARG scheduler_service_package_dist_name
ARG scheduler_service_package_version_constraint

WORKDIR /code

COPY ./entrypoint.sh entrypoint.sh

# Copy custom built packages from external sources image
COPY --from=sources /DIST /DIST

RUN apk update \
    && apk add --no-cache openssl bash libffi-dev musl-dev libstdc++ git openblas-dev proj proj-dev proj-util gdal-dev  \
    && rm -rf /var/cache/apk/* \
    && alias python=python3 \
    && pip3 install --no-cache-dir --upgrade pip \
    # Do websockets package separately first to work around some current issues (2/1/2022) \
    # TODO: fix root cause for problem this works around \
    && pip3 install websockets \
    # Install service package, along with custom and generally available dependencies, which should all be in /DIST \
    && pip3 install --no-cache-dir --find-links=/DIST "${scheduler_service_package_dist_name}${scheduler_service_package_version_constraint}" \
    # TODO: this is a workaround, and may have side effects (transitive dependency issue with aiohttp and redis) \
    && pip3 install --no-cache-dir aiohttp==3.8.1 \
    # After installing everything needed from /DIST, clean up ... \
    && rm -r /DIST \
    && mkdir -p ~/.ssh \
    && printf "Host *\n        ServerAliveInterval 300\n        ServerAliveCountMax 2\n" >> ~/.ssh/config

# TODO: when image tagging/versioning is improved, look at keeping this in a "debug" image only
# Copy this to have access to debugging pydevd egg
COPY --from=sources /dmod /dmod_src
RUN if [ -e /dmod_src/python/pydevd-pycharm.egg ]; then mv /dmod_src/python/pydevd-pycharm.egg /. ; fi \
    && rm -rf /dmod_src

ENTRYPOINT ["/code/entrypoint.sh"]
