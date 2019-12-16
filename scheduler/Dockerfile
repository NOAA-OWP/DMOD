# problem using the current registry (127.0.0.1:5000), apparently due to the ':'
# which Docker thinks is an invalid --from value in the multi-stage copy step
ARG docker_internal_registry
FROM ${docker_internal_registry}/nwmaas-py-sources as sources

FROM python:3.7-alpine
ARG comms_package_name
ARG scheduler_package_dist_name

WORKDIR /code

COPY entrypoint.sh entrypoint.sh
COPY requirements.txt requirements.txt
COPY ssl/scheduler/ /ssl/scheduler/

# Copy custom built packages from external sources image
COPY --from=sources /DIST /DIST

RUN apk update \
    && apk add --no-cache openssl bash \
    && rm -rf /var/cache/apk/* \
    && alias python=python3 \
    && pip3 install --no-cache-dir --upgrade pip \
    # Install custom and generally available packages, starting with any custom from external source image \
    && pip3 install --no-cache-dir --find-links=/DIST/comms ${comms_package_name} \
    && pip3 install --no-cache-dir --find-links=/DIST/scheduler ${scheduler_package_dist_name} \
    # After eventually installing all custom packages like this, clean up ... \
    && rm -r /DIST \
    && mkdir -p ~/.ssh \
    && printf "Host *\n        ServerAliveInterval 300\n        ServerAliveCountMax 2\n" >> ~/.ssh/config

ENTRYPOINT ["/code/entrypoint.sh"]
