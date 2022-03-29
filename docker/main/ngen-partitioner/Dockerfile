ARG DOCKER_INTERNAL_REGISTRY
FROM ${DOCKER_INTERNAL_REGISTRY}/ngen-deps:latest

#Passing the ARG variables from compose via .env file will squash these defaults with empty strings
#Seems like the work around is to replicate the default values in the build env, or to check for
#empty and set to default as is shown commented out below.
ENV PATH "${WORKDIR}/bin:${PATH}"

ARG REPO_URL=https://github.com/NOAA-OWP/ngen.git
ARG BRANCH=master
ARG COMMIT

ENV BOOST_ROOT=${WORKDIR}/boost

ARG BUILD_PARALLEL_JOBS
ARG BMI_C_ACTIVE=ON
ARG PYTHON_ACTIVE=ON
ARG MPI_ACTIVE=ON
# Note that, at least for now, these are off by default until the functionality is both generally available and needed
ARG BMI_FORTRAN_ACTIVE=OFF
ARG ROUTING_ACTIVE=OFF
ARG PARTITIONER_EXECUTABLE

RUN git clone --single-branch --branch $BRANCH $REPO_URL \
    && cd ./ngen \
    && if [ "x$COMMIT" != "x" ]; then git checkout $COMMIT; fi \
    && git submodule update --init \
    && cmake -B cmake_build \
                -DBMI_FORTRAN_ACTIVE:BOOL=${BMI_FORTRAN_ACTIVE} \
                -DBMI_C_LIB_ACTIVE:BOOL=${BMI_C_ACTIVE} \
                -DNGEN_ACTIVATE_PYTHON:BOOL=${PYTHON_ACTIVE} \
                -DNGEN_ACTIVATE_ROUTING:BOOL=${ROUTING_ACTIVE} \
                -DUDUNITS_ACTIVE:BOOL=ON \
                -S . -DCMAKE_INSTALL_PREFIX=${WORKDIR} \
    && cmake --build cmake_build --target ${PARTITIONER_EXECUTABLE} -- -j ${BUILD_PARALLEL_JOBS} \
    #FIXME remove the data copy, only there for temporary testing \
    && mkdir ${WORKDIR}/bin && cp cmake_build/${PARTITIONER_EXECUTABLE} ${WORKDIR}/bin \
    && cd ${WORKDIR} && rm -rf ngen

USER root
# Remove the boost headers now that ngen is compiled
RUN rm -rf ${BOOST_ROOT} && echo "export PATH=${PATH}" >> /etc/profile
USER ${USER}
COPY --chown=${USER} entrypoint.sh ${WORKDIR}
RUN chmod +x ${WORKDIR}/entrypoint.sh
ENV PATH=${WORKDIR}:$PATH
ENV NGEN_PART_EXECUTABLE="${PARTITIONER_EXECUTABLE}"
ENTRYPOINT ["./entrypoint.sh"]
