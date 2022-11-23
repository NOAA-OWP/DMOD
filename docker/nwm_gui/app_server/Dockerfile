# Need this extra stage basically to alias the "sources" stage, as there is a
# problem using the current registry (127.0.0.1:5000), apparently due to the ':'
# which Docker thinks is an invalid --from value in the multi-stage copy step
ARG docker_internal_registry
FROM ${docker_internal_registry}/dmod-py-sources as sources

FROM python:3.8-slim as base
# Update the aptitude package listing so that packages may be loaded and installed
# Install python binaries to make pip installs a little smoother
RUN apt-get update && apt-get install -y python3-django netcat

# Move to a new directory at "/usr/wres-gui"
WORKDIR /usr/maas_portal
# Copy the requirements.txt file in the current directory for the application to the
# working directory of the docker image (/usr/wres-gui)
COPY ./python/gui/dependencies.txt ./
# Install all the python packages described in the requirements file
RUN pip install -r dependencies.txt
# Ensures that raw data directed at a terminal moves in one go rather than being buffered
ENV PYTHONUNBUFFERED 1

# Slurp (or set default) wheel package names ...
ARG core_package_name=dmod-core
ARG comms_package_name=dmod-communication
ARG client_package_name=dmod-client

# Copy custom built packages from external sources image
COPY --from=sources /DIST /DIST
RUN pip install --upgrade --find-links=/DIST ${core_package_name} \
    && pip install --upgrade --find-links=/DIST ${comms_package_name} \
    && pip install --upgrade --find-links=/DIST ${client_package_name} \
    # After eventually installing all dist files like this, clean up ... \
    && rm -rf /DIST

# Copy selected portions of the project into the working directory (/usr/maas_portal)
COPY ./python/gui/manage.py ./
COPY ./python/gui/static ./static
COPY ./python/gui/maas_experiment ./maas_experiment
COPY ./python/gui/MaaS ./MaaS
COPY ./docker/nwm_gui/app_server/entrypoint.sh ./
COPY ./docker/nwm_gui/app_server/client_debug_helper.py ./

RUN echo "request-service:" > .dmod_client_config.yml \
    && echo "  hostname: 'request-service'" >> .dmod_client_config.yml \
    && echo "  port: 3012" >> .dmod_client_config.yml \
    && echo "  ssl-dir: '/usr/maas_portal/ssl'" >> .dmod_client_config.yml

# TODO: when image tagging/versioning is improved, look at keeping this in a "debug" image only
# Copy this to have access to debugging pydevd egg
COPY --from=sources /dmod /dmod_src
RUN if [ -e /dmod_src/python/pydevd-pycharm.egg ]; then mv /dmod_src/python/pydevd-pycharm.egg /. ; fi \
    && rm -rf /dmod_src

# Set the entry point so that it is run every time the container is started
ENTRYPOINT ["/usr/maas_portal/entrypoint.sh"]
