# Need this extra stage basically to alias the "sources" stage, as there is a
# problem using the current registry (127.0.0.1:5000), apparently due to the ':'
# which Docker thinks is an invalid --from value in the multi-stage copy step
ARG docker_internal_registry
FROM ${docker_internal_registry}/nwmaas-py-sources as sources

FROM python:3.8-slim
# Slurp (or set default) wheel package name ...
ARG comms_package_name=nwmaas-communication
# Copy custom built packages from external sources image
COPY --from=sources /DIST /DIST
RUN pip install --upgrade --find-links=/DIST/internal_deps ${comms_package_name} \
    # After eventually installing all dist files like this, clean up ... \
    && rm -r /DIST
# Update the aptitude package listing so that packages may be loaded and installed
# Install python binaries to make pip installs a little smoother
RUN apt-get update && apt-get install -y python3-django
# Move to a new directory at "/usr/wres-gui"
WORKDIR /usr/maas_portal
# Copy the requirements.txt file in the current directory for the application to the
# working directory of the docker image (/usr/wres-gui)
COPY ./requirements.txt ./
# Install all the python packages described in the requirements file
RUN pip install -r requirements.txt
# Ensures that raw data directed at a terminal moves in one go rather than being buffered
ENV PYTHONUNBUFFERED 1
# Copy selected portions of the project into the working directory (/usr/maas_portal)
COPY ./manage.py ./
COPY ./static ./static
COPY ./ssl ./ssl
COPY ./maas_experiment ./maas_experiment
COPY ./MaaS ./MaaS
COPY ./entrypoint.sh ./
# Set the entry point so that it is run every time the container is started
ENTRYPOINT ["/usr/maas_portal/entrypoint.sh"]
