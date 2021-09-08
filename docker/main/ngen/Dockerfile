ARG DOCKER_INTERNAL_REGISTRY
#FIXME is base no longer nwm specific??? How about deps?
#Base is missing a few simple deps, like git...
#FROM ${DOCKER_INTERNAL_REGISTRY}/nwm-base
FROM ${DOCKER_INTERNAL_REGISTRY}/ngen-deps:latest

#Passing the ARG variables from compose via .env file will squash these defaults with empty strings
#Seems like the work around is to replicate the default values in the build env, or to check for
#empty and set to default as is shown commented out below.
#
# ***************** Important Note: there are several more arg declared below.
# ***************** They are separated like this to support better build caching.
#
ENV PATH "${WORKDIR}/bin:${PATH}"

ARG REPO_URL=https://github.com/NOAA-OWP/ngen.git
ARG BRANCH=master
ARG COMMIT
RUN git clone --single-branch --branch $BRANCH $REPO_URL \
    && cd ./ngen \
    && if [ "x$COMMIT" != "x" ]; then git checkout $COMMIT; fi

# TODO: fix this to just update --init all submodules once alt-modular gets removed appropriately
RUN cd ./ngen \
    && git submodule update --init --recursive -- test/googletest \
    && git submodule update --init -- extern/pybind11 \
    && git submodule update --init -- extern/t-route

RUN cd ./ngen \
    && python3 -m venv venv \
    && source venv/bin/activate \
    && pip install --upgrade pip \
    && pip install /wheel_dist/numpy*.whl

ARG BUILD_PARALLEL_JOBS
ARG BMI_C_ACTIVE=ON
ARG PYTHON_ACTIVE=ON
ARG MPI_ACTIVE=ON
# Note that, at least for now, these are off by default until the functionality is both generally available and needed
ARG BMI_FORTRAN_ACTIVE=OFF
ARG ROUTING_ACTIVE=OFF

RUN cd ./ngen \
    && source venv/bin/activate \
    && cmake -B cmake-build \
            -DMPI_ACTIVE:BOOL=${MPI_ACTIVE} \
            -DBMI_FORTRAN_ACTIVE:BOOL=${BMI_FORTRAN_ACTIVE} \
            -DBMI_C_LIB_ACTIVE:BOOL=${BMI_C_ACTIVE} \
            -DNGEN_ACTIVATE_PYTHON:BOOL=${PYTHON_ACTIVE} \
            -DNGEN_ACTIVATE_ROUTING:BOOL=${ROUTING_ACTIVE} \
            -S . -DCMAKE_INSTALL_PREFIX=${WORKDIR} \
    && cmake --build cmake-build -j ${BUILD_PARALLEL_JOBS} \
    #Run the tests, if they fail, the image build fails \
    && cmake-build/test/test_all \
    #FIXME remove the data copy, only there for temporary testing \
    && mkdir ${WORKDIR}/bin && cp cmake-build/ngen ${WORKDIR}/bin && cp -r data ${WORKDIR}/data \
    && cd $WORKDIR && rm -rf ngen boost

USER root
#Remove the boost headers now that ngen is compiled
RUN rm -rf ${BOOST_ROOT}
RUN rm -rf /wheel_dist
RUN echo "export PATH=${PATH}" >> /etc/profile
USER ${USER}
COPY --chown=${USER} entrypoint.sh ${WORKDIR}
RUN chmod +x ${WORKDIR}/entrypoint.sh
WORKDIR ${WORKDIR}
ENV PATH=${WORKDIR}:$PATH
ENTRYPOINT ["entrypoint.sh"]
CMD [""]
