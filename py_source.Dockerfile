FROM python:3.8-alpine as basis

# Create intermediate Docker build stage for building nwm_maas_comms wheel distribution for pip
FROM basis as build_comms
# Copy source
COPY ./communication ./nwm_service/communication
# Move to source dir
WORKDIR ./nwm_service/communication
# Create easy-to-find dist dir at root, install build dependencies, run build helper script, and move wheel file to easy-to-find location
RUN mkdir /comms_dist && pip install --upgrade websockets jsonschema setuptools wheel && ./build.sh build && mv ./dist/*.whl /comms_dist/.

# Final Docker build stage
FROM basis
# Copy complete python source packages to location
COPY ./communication ./gui ./request_handler ./scheduler /nwm_service/
# And for every build dist/wheel package copy wheel file into analogous location for this stage
COPY --from=build_comms /comms_dist /DIST/comms