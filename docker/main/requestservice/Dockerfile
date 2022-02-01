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

# Install custom and generally available packages, starting with any custom from external source image
# Do these separately first to work around some issues
# TODO: fix root cause for problem this works around
RUN pip install websockets Deprecated \
    && pip install --no-index --find-links=/DIST "${request_service_package_name}${request_service_package_version_constraint}" \
    # After eventually installing all custom packages like this, clean up ... \
    && rm -r /DIST

EXPOSE ${DOCKER_REQUESTS_CONTAINER_PORT:-3012}

ENTRYPOINT ["/code/entrypoint.sh"]
