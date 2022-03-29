ARG docker_internal_registry
# Making this an "empty" stage just so it can be copied-from in the next stage
FROM ${docker_internal_registry}/dmod-py-sources as sources

FROM python:3.8-alpine3.15

ARG partitioner_service_package_name
ARG partitioner_service_listener_port

# Currently need Git installed to retrieve some package transitive dependencies
RUN apk --no-cache --update-cache add git

WORKDIR /code

# Copy custom built packages from previous stage FROM external sources image
COPY --from=sources /DIST /DIST

# Install custom and generally available packages, starting with any custom from external source image
RUN pip install --no-index --find-links=/DIST ${partitioner_service_package_name} \
    # After eventually installing all custom packages like this, clean up ... \
    && rm -r /DIST

EXPOSE ${partitioner_service_listener_port}

ENTRYPOINT [ "python3", "-m", "${partitioner_service_module_name}" ]