# Need this extra stage basically to alias the "sources" stage, as there is a
# problem using the current registry (127.0.0.1:5000), apparently due to the ':'
# which Docker thinks is an invalid --from value in the multi-stage copy step
ARG docker_internal_registry
FROM ${docker_internal_registry}/dmod-py-sources as sources

FROM rockylinux:9.1

# Do this separately at the beginning to get some caching help
RUN dnf update -y && \
    dnf install -y python3-pip git \
    && ln -s /usr/bin/python3 /usr/bin/python

RUN dnf install -y 'dnf-command(config-manager)' \
    && dnf config-manager --set-enabled crb \
    && dnf install -y epel-release \
    && dnf install -y netcat libpq-devel \
    && dnf clean -y all

# Move to a new directory at "/usr/wres-gui"
WORKDIR /usr/maas_portal
# Copy the requirements.txt file in the current directory for the application to the
# working directory of the docker image (/usr/wres-gui)
COPY ./python/gui/dependencies.txt ./
# Install all the python packages described in the requirements file
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r dependencies.txt
# Ensures that raw data directed at a terminal moves in one go rather than being buffered
ENV PYTHONUNBUFFERED 1

# Slurp (or set default) wheel package names ...
ARG comms_package_name=dmod-communication
ARG client_package_name=dmod-client

# Copy custom built packages from external sources image
COPY --from=sources /DIST /DIST
RUN pip install --no-cache-dir --upgrade --find-links=/DIST ${comms_package_name} \
    && pip install --no-cache-dir --upgrade --find-links=/DIST ${client_package_name} \
    # After eventually installing all dist files like this, clean up ... \
    && rm -rf /DIST

# Copy selected portions of the project into the working directory (/usr/maas_portal)
COPY ./python/gui/manage.py ./
COPY ./python/gui/static ./static
COPY ./python/gui/maas_experiment ./maas_experiment
COPY ./python/gui/MaaS ./MaaS
COPY ./docker/nwm_gui/app_server/entrypoint.sh ./
COPY ./docker/nwm_gui/app_server/client_debug_helper.py ./

ENV PYCHARM_DEBUG_EGG=/pydevd-pycharm.egg
ENV REQ_SRV_SSL_DIR=${WORKDIR}/request_service_ssl
COPY ./ssl/requestservice ${REQ_SRV_SSL_DIR}

# TODO: move to heredoc syntax once confirmed it's reasonable to expect all environments run sufficiently recent Docker
RUN     echo '{'                                                            > .dmod_client_config.json \
    &&  if [ ${PYCHARM_REMOTE_DEBUG_ACTIVE:-} = 'true' ]; then \
            echo '    "remote-debug": {'                                    >> .dmod_client_config.json ; \
            echo "        \"remote-debug\": \"${PYCHARM_DEBUG_EGG:?}\","    >> .dmod_client_config.json ; \
            echo "        \"port\": \"${MAAS_PORTAL_DEBUG_PORT:?}\","       >> .dmod_client_config.json ; \
            echo "        \"host\": \"${MAAS_PORTAL_DEBUG_HOST:?}\""        >> .dmod_client_config.json ; \
            echo '    },'                                                   >> .dmod_client_config.json ; \
        fi \
    &&  echo '    "request-service": {'                                     >> .dmod_client_config.json \
    &&  echo '        "protocol": "wss",'                                   >> .dmod_client_config.json \
    &&  echo "        \"pem\": \"${REQ_SRV_SSL_DIR}/certificate.pem\","     >> .dmod_client_config.json \
    &&  echo "        \"port\": ${MAAS_ENDPOINT_PORT},"                     >> .dmod_client_config.json \
    &&  echo '        "hostname": "request-service",'                       >> .dmod_client_config.json \
    &&  echo '    }'                                                        >> .dmod_client_config.json \
    &&  echo '}'                                                            >> .dmod_client_config.json

# TODO: when image tagging/versioning is improved, look at keeping this in a "debug" image only
# Copy this to have access to debugging pydevd egg
COPY --from=sources /dmod /dmod_src
RUN if [ -e /dmod_src/python/pydevd-pycharm.egg ]; then mv /dmod_src/python/pydevd-pycharm.egg ${PYCHARM_DEBUG_EGG} ; fi \
    && rm -rf /dmod_src

# Set the entry point so that it is run every time the container is started
ENTRYPOINT ["/usr/maas_portal/entrypoint.sh"]
