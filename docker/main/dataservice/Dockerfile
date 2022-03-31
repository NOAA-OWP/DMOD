ARG docker_internal_registry
################################################################################################################
FROM ${docker_internal_registry}/dmod-py-sources as sources

################################################################################################################
FROM python:3.8-alpine3.15
ARG service_package_name
ARG service_package_constraint
WORKDIR /code
COPY ./entrypoint.sh entrypoint.sh
COPY --from=sources /DIST /DIST
RUN apk update \
    && apk add --no-cache openssl git g++ libffi-dev \
    && chmod u+x entrypoint.sh \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --find-links=/DIST "${service_package_name}${service_package_constraint}" \
    && rm -rf /DIST
ENTRYPOINT ["/code/entrypoint.sh"]