# problem using the current registry (127.0.0.1:5000), apparently due to the ':'
# which Docker thinks is an invalid --from value in the multi-stage copy step
ARG docker_internal_registry
FROM ${docker_internal_registry}/nwmaas-py-sources as sources

FROM python:3.7-alpine
ARG comms_package_name
# A base SSL directory, which may or may not contain subdirectories specifically for service- or client-side certs
ARG container_base_ssl_directory=/ssl

WORKDIR /code

COPY entrypoint.sh entrypoint.sh
COPY request_handler/ request_handler/
COPY requirements.txt requirements.txt
COPY ssl/ ${container_base_ssl_directory}/
COPY tests/ tests/

# Copy custom built packages from external sources image
COPY --from=sources /DIST /DIST

# Install custom and generally available packages, starting with any custom from external source image
RUN pip install --no-cache-dir --find-links=/DIST/comms ${comms_package_name} \
    # After eventually installing all custom packages like this, clean up ... \
    && rm -r /DIST \
    # Then also pull in any other dependencies via pip \
    && pip install --no-cache-dir --requirement requirements.txt

EXPOSE ${DOCKER_REQUESTS_CONTAINER_PORT:-3012}

ENTRYPOINT ["/code/entrypoint.sh"]
