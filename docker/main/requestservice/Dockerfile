# problem using the current registry (127.0.0.1:5000), apparently due to the ':'
# which Docker thinks is an invalid --from value in the multi-stage copy step
ARG docker_internal_registry
FROM ${docker_internal_registry}/dmod-py-sources as sources

FROM python:3.8-alpine
ARG comms_package_name
ARG access_package_name
ARG externalrequests_package_name
ARG request_service_package_name
ARG request_service_package_version_constraint
# A base SSL directory, which may or may not contain subdirectories specifically for service- or client-side certs
ARG container_base_ssl_directory=/ssl

WORKDIR /code

COPY ./entrypoint.sh entrypoint.sh

# Copy custom built packages from external sources image
COPY --from=sources /DIST /DIST

# Copy this to have access to debugging pydevd egg
# TODO: when image tagging/versioning is improved, look at keeping this in a "debug" image only
COPY --from=sources /dmod /dmod_src

# Install custom and generally available packages, starting with any custom from external source image
# First install the Pycharm debug helper util egg, if it is there
# TODO: when image tagging/versioning is improved, look at keeping this in a "debug" image only
RUN if [ -e /dmod_src/python/pydevd-pycharm.egg ]; then mv /dmod_src/python/pydevd-pycharm.egg /. ; fi \
    && if [ -d /dmod_src ]; then rm -rf /dmod_src ; fi \
    # Install these separately before the service package (and its other deps) to work around a problem issue \
    # TODO: fix root cause for problem this works around  \
    && pip install websockets Deprecated  \
    && pip install --no-index --find-links=/DIST "${request_service_package_name}${request_service_package_version_constraint}" \
    # After eventually installing all custom packages like this, clean up ... \
    && rm -r /DIST

EXPOSE ${DOCKER_REQUESTS_CONTAINER_PORT:-3012}

ENTRYPOINT ["/code/entrypoint.sh"]
