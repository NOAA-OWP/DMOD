ARG DOCKER_INTERNAL_REGISTRY
#FIXME is base no longer nwm specific??? How about deps?
#Base is missing a few simple deps, like git...
#FROM ${DOCKER_INTERNAL_REGISTRY}/nwm-base
FROM ${DOCKER_INTERNAL_REGISTRY}/ngen-deps:latest

#Passing the ARG variables from compose via .env file will squash these defaults with empty strings
#Seems like the work around is to replicate the default values in the build env, or to check for
#empty and set to default as is shown commented out below.
ARG REPO_URL=https://github.com/NOAA-OWP/ngen.git
ARG BRANCH=master
ARG COMMIT
ARG BUILD_PARALLEL_JOBS
ENV PATH "${WORKDIR}/bin:${PATH}"
ENV BOOST_ROOT=${WORKDIR}/boost

ARG NGEN_ACTIVATE_C="ON"
ARG NGEN_ACTIVATE_FORTRAN="ON"
ARG NGEN_ACTIVATE_PYTHON="ON"
ARG NGEN_MPI_ACTIVE="ON"
ARG NGEN_ROUTING_ACTIVE="ON"
ARG NGEN_UDUNITS_ACTIVE="ON"

ARG BUILD_NOAH_OWP="true"
ARG BUILD_CFE="true"
ARG BUILD_TOPMODEL="true"

# TODO: add something to build to pull (and build) in the submodules (except googletest) when needed based on build config

# Swap or override this as needed (below are the "standard" types from
#   https://cmake.org/cmake/help/latest/manual/cmake-buildsystem.7.html#default-and-custom-configurations)
#ARG NGEN_BUILD_CONFIG_TYPE="Debug"
ARG NGEN_BUILD_CONFIG_TYPE="Release"
#ARG NGEN_BUILD_CONFIG_TYPE="RelWithDebInfo"
#ARG NGEN_BUILD_CONFIG_TYPE="MinSizeRel"

RUN git clone --single-branch --branch $BRANCH $REPO_URL \
    && cd ./ngen \
    && if [ "x$COMMIT" != "x" ]; then git checkout $COMMIT; fi \
    && if [ "${NGEN_ACTIVATE_PYTHON}" == "ON" ]; then pip install -r extern/test_bmi_py/requirements.txt; fi \
    && git submodule update --init test/googletest \
    && git submodule update --init \
    && echo "#!/bin/bash" > build_sub \
    && echo "cmake -B \$1/cmake_build -DCMAKE_BUILD_TYPE=${NGEN_BUILD_CONFIG_TYPE} -S \$1 && cmake --build \$1/cmake_build" >> build_sub \
    && chmod u+x build_sub \
    &&  if [ "${NGEN_ACTIVATE_FORTRAN}" == "ON" ]; then \
            ./build_sub extern/iso_c_fortran_bmi; \
            if [ "${BUILD_NOAH_OWP}" == "true" ] ; then ./build_sub extern/noah-owp-modular; fi; \
        fi \
    &&  if [ "${NGEN_ACTIVATE_C}" == "ON" ]; then \
            if [ "${BUILD_CFE}" == "true" ] ; then ./build_sub extern/cfe; fi; \
            if [ "${BUILD_TOPMODEL}" == "true" ] ; then ./build_sub extern/topmodel; fi; \
        fi \
    && cmake -B cmake_build -S . \
            -DMPI_ACTIVE:BOOL=${NGEN_MPI_ACTIVE} \
            -DBMI_C_LIB_ACTIVE:BOOL=${NGEN_ACTIVATE_C} \
            -DBMI_FORTRAN_ACTIVE:BOOL=${NGEN_ACTIVATE_FORTRAN} \
            -DNGEN_ACTIVATE_PYTHON:BOOL=${NGEN_ACTIVATE_PYTHON} \
            -DNGEN_ACTIVATE_ROUTING:BOOL=${NGEN_ROUTING_ACTIVE} \
            -DUDUNITS_ACTIVE:BOOL=${NGEN_UDUNITS_ACTIVE} \
            -DCMAKE_INSTALL_PREFIX=${WORKDIR} \
    && cmake --build cmake_build -j ${BUILD_PARALLEL_JOBS} \
    #Run the tests, if they fail, the image build fails \
    && cmake_build/test/test_unit \
    &&  if [ "${NGEN_ACTIVATE_C}" == "ON" ]; then \
            ./build_sub extern/test_bmi_c; \
            cmake_build/test/test_bmi_c; \
        fi \
    &&  if [ "${NGEN_ACTIVATE_FORTRAN}" == "ON" ]; then \
            ./build_sub extern/test_bmi_fortran; \
            cmake_build/test/test_bmi_fortran; \
        fi \
    &&  if [ "${NGEN_ACTIVATE_PYTHON}" == "ON" ]; then \
            ./build_sub extern/test_bmi_py; \
            cmake_build/test/test_bmi_python; \
        fi \
    &&  if [ "${NGEN_ACTIVATE_C}" == "ON" ] && [ "${NGEN_ACTIVATE_FORTRAN}" == "ON" ] && [ "${NGEN_ACTIVATE_PYTHON}" == "ON" ]; then \
            cmake_build/test/test_bmi_multi; \
        fi \
    #FIXME remove the data copy, only there for temporary testing \
    && mkdir ${WORKDIR}/bin && cp cmake_build/ngen ${WORKDIR}/bin && cp -r data ${WORKDIR}/data \
    && cd $WORKDIR && rm -rf ngen boost

USER root
# Remove the boost headers now that ngen is compiled; also update path and make sure dataset directory is there
RUN rm -rf ${BOOST_ROOT} && echo "export PATH=${PATH}" >> /etc/profile
USER ${USER}
COPY --chown=${USER} entrypoint.sh ${WORKDIR}
RUN chmod +x ${WORKDIR}/entrypoint.sh
WORKDIR ${WORKDIR}
ENV PATH=${WORKDIR}:$PATH
ENTRYPOINT ["entrypoint.sh"]
CMD [""]
