##### Create base level intermediate build stage
FROM python:3.8-alpine as basis
# Needed for sourced functions used by package-specific build scripts in later stages
COPY ./scripts /nwm_service/scripts
# Along with setup and wheel to build, install all pip dependencies any/all built packages will need (i.e., once)
RUN pip install --upgrade docker Faker jsonschema redis setuptools wheel

##### Create intermediate Docker build stage for building nwmaas-communication wheel distribution for pip
FROM basis as build_comms
ARG comms_package_name
# Set this in the environment, as it's required by the ./build.sh script, but probably won't get sourced from an .env
ENV PYTHON_PACKAGE_DIST_NAME_COMMS=${comms_package_name}
# Copy source
COPY ./communication ./nwm_service/communication
# Move to source dir
WORKDIR ./nwm_service/communication
# Create easy-to-find dist dir at root, install build dependencies, run build helper script, and move wheel file to easy-to-find location
RUN mkdir /comms_dist \
    && ./build.sh --sys build \
    && mv ./dist/*.whl /comms_dist/.

##### Create intermediate Docker build stage for later stages that have nwmaas-communication as a build dependency
FROM basis as has_comms_dependency
ARG comms_package_name
COPY --from=build_comms /comms_dist /DIST/comms
RUN pip install --no-cache-dir --find-links=/DIST/comms ${comms_package_name}

##### Create intermediate Docker build stage for building nwmaas-request-handler wheel distribution for pip
FROM has_comms_dependency as build_request_handler
ARG request_handler_package_name
# Set this in the environment, as it's required by the ./build.sh script, but probably won't get sourced from an .env
ENV PYTHON_PACKAGE_DIST_NAME_REQUEST_HANDLER=${request_handler_package_name}
# Copy source
COPY ./request_handler ./nwm_service/request_handler
# Move to source dir
WORKDIR ./nwm_service/request_handler
# Create easy-to-find dist dir at root, install build dependencies, run build helper script, and move wheel file to easy-to-find location
RUN mkdir /request_handler_dist \
    # Remember, from previous intermediate Docker build stage, nwmaas-communication will already be installed \
    && ./build.sh --sys build \
    && mv ./dist/*.whl /request_handler_dist/.

##### Create intermediate Docker build stage for building nwmaas-scheduler wheel distribution for pip
FROM has_comms_dependency as build_scheduler
ARG scheduler_package_dist_name
# Set this in the environment, as it's required by the ./build.sh script, but probably won't get sourced from an .env
ENV PYTHON_PACKAGE_DIST_NAME_SCHEDULER=${scheduler_package_dist_name}
# Copy source
COPY ./scheduler ./nwm_service/scheduler
# Move to source dir
WORKDIR ./nwm_service/scheduler
# Create easy-to-find dist dir at root, install build dependencies, run build helper script, and move wheel file to easy-to-find location
RUN mkdir /scheduler_dist \
    # Remember, from previous intermediate Docker build stage, nwmaas-communication will already be installed \
    && ./build.sh --sys build \
    && mv ./dist/*.whl /scheduler_dist/.

#### Create final Docker build stage for desired image
FROM python:3.8-alpine
# Copy complete python source packages to location
COPY ./communication ./gui ./request_handler ./scheduler /nwm_service/
# And for every build dist/wheel package copy wheel file into analogous location for this stage
COPY --from=build_comms /comms_dist /DIST/comms
COPY --from=build_request_handler /request_handler_dist /DIST/request_handler
COPY --from=build_scheduler /scheduler_dist /DIST/scheduler