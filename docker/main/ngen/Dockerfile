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
ARG BOOST_VERSION=1.72.0
ENV BOOST_ROOT=${WORKDIR}/boost

RUN wget https://dl.bintray.com/boostorg/release/${BOOST_VERSION}/source/boost_${BOOST_VERSION//./_}.tar.gz \
    #### \
    # Get boost headers \
    #### \
    && mkdir -p ${WORKDIR}/boost \
    && tar zxf boost_${BOOST_VERSION//./_}.tar.gz -C ./boost --strip-components=1 \
    && rm boost_${BOOST_VERSION//./_}.tar.gz \
    && git clone --single-branch --branch $BRANCH $REPO_URL \
    && cd ./ngen \
    && git submodule update --init --recursive -- test/googletest \
    && if [ "x$COMMIT" != "x" ]; then git checkout $COMMIT; fi \
    && cmake -B cmake-build -S . -DCMAKE_INSTALL_PREFIX=${WORKDIR} \
    && cmake --build cmake-build -j ${BUILD_PARALLEL_JOBS} \
    #Run the tests, if they fail, the image build fails \
    && cmake-build/test/test_all \
    #FIXME remove the data copy, only there for temporary testing \
    && mkdir ${WORKDIR}/bin && cp cmake-build/ngen ${WORKDIR}/bin && cp -r data ${WORKDIR}/data \
    && cd $WORKDIR && rm -rf ngen boost

USER root
#Remove the boost headers now that ngen is compiled
RUN rm -rf ${BOOST_ROOT}
RUN echo "export PATH=${PATH}" >> /etc/profile
USER ${USER}
COPY --chown=${USER} entrypoint.sh ${WORKDIR}
RUN chmod +x ${WORKDIR}/entrypoint.sh
WORKDIR ${WORKDIR}
ENV PATH=${WORKDIR}:$PATH
ENTRYPOINT ["entrypoint.sh"]
CMD [""]
