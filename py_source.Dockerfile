##### Create base level intermediate build stage
FROM python:3.7-alpine as basis
# Needed for sourced functions used by build scripts in later stages
COPY ./scripts /nwm_service/scripts
# Copy library package sources
COPY ./lib /nwm_service/lib
# Copy project requirements file, which should have everything needed to build any package within project
COPY ./requirements.txt /nwm_service/requirements.txt
# Move to source dir
WORKDIR ./nwm_service
# Along with setup and wheel to build, install all project pip dependencies for package building later
RUN mkdir /DIST && pip download --no-cache-dir --destination-directory /DIST -r /nwm_service/requirements.txt

##### Create intermediate Docker build stage for building and installing wheel distributions for internal dependency packages
FROM basis as internal_deps
ARG comms_package_name
ARG access_package_name
ARG externalrequests_package_name
ARG scheduler_package_name
RUN for p in communication access externalrequests scheduler; do \
        ./scripts/dist_package.sh --sys lib/${p} && mv lib/${p}/dist/*.whl /DIST/.; \
    done

##### Create intermediate Docker build stage for building nwmaas-request-handler wheel distribution for pip
FROM internal_deps as build_request_service
ARG request_service_package_name
# Set this in the environment, as it's required by the ./build.sh script, but probably won't get sourced from an .env
ENV PYTHON_PACKAGE_DIST_NAME_REQUEST_SERVICE=${request_service_package_name}
# Copy source
COPY ./requestservice /nwm_service/requestservice
# Create easy-to-find dist dir at root, install build dependencies, run build helper script, and move wheel file to easy-to-find location
RUN mkdir /requestservice_dist \
    && ./scripts/dist_package.sh --sys ./requestservice \
    && mv ./requestservice/dist/*.whl /requestservice_dist/.

##### Create intermediate Docker build stage for building nwmaas-schedulerservice wheel distribution for pip
FROM internal_deps as build_scheduler_service
ARG scheduler_service_package_dist_name
# Set this in the environment, as it's required by the ./build.sh script, but probably won't get sourced from an .env
ENV PYTHON_PACKAGE_DIST_NAME_SCHEDULER_SERVICE=${scheduler_service_package_dist_name}
# Copy source
COPY ./schedulerservice /nwm_service/schedulerservice
# Create easy-to-find dist dir at root, install build dependencies, run build helper script, and move wheel file to easy-to-find location
RUN mkdir /schedulerservice_dist \
    && ./scripts/dist_package.sh --sys ./schedulerservice \
    && mv ./schedulerservice/dist/*.whl /schedulerservice_dist/.

#### Create final Docker build stage for desired image
FROM python:3.8-alpine
# Copy complete python source packages to location
COPY ./lib ./gui ./requestservice ./schedulerservice /nwm_service/
# And for every build dist/wheel package copy wheel file into analogous location for this stage
COPY --from=internal_deps /DIST/* /DIST/
COPY --from=build_request_service /requestservice_dist/* /DIST/
COPY --from=build_scheduler_service /schedulerservice_dist/* /DIST/