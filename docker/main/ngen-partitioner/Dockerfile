ARG DOCKER_INTERNAL_REGISTRY
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

ARG PARTITIONER_EXECUTABLE

# TODO: A lot overlaps with the main Ngen image ... see about what can be combined.
# TODO:     That will probably also require adjusting the tagging to be somewhat based on checkout.

#RUN wget https://dl.bintray.com/boostorg/release/${BOOST_VERSION}/source/boost_${BOOST_VERSION//./_}.tar.gz \
RUN wget https://downloads.sourceforge.net/project/boost/boost/${BOOST_VERSION}/boost_${BOOST_VERSION//./_}.tar.gz \
    && mkdir -p ${WORKDIR}/boost \
    && tar zxf boost_${BOOST_VERSION//./_}.tar.gz -C ./boost --strip-components=1 \
    && rm boost_${BOOST_VERSION//./_}.tar.gz

RUN git clone --single-branch --branch $BRANCH $REPO_URL \
    && cd ./ngen \
    && git submodule update --init --recursive -- test/googletest \
    && if [ "x$COMMIT" != "x" ]; then git checkout $COMMIT; fi

RUN cmake -B ${WORKDIR}/ngen/cmake-build -S ${WORKDIR}/ngen -DCMAKE_INSTALL_PREFIX=${WORKDIR}

RUN cmake --build ${WORKDIR}/ngen/cmake-build --target ${PARTITIONER_EXECUTABLE} -j ${BUILD_PARALLEL_JOBS} \
    && mkdir ${WORKDIR}/bin \
    && cp ${WORKDIR}/ngen/cmake-build/${PARTITIONER_EXECUTABLE} ${WORKDIR}/bin/ngen_partitioner

# TODO: (later) need to have option for whether just partition file or separated into partitioned hydrofabric files

# TODO: figure out what of this (copied from ngen image) needs to stay and what needs to go
USER root
#Remove the boost headers now that ngen is compiled
RUN rm -rf ${BOOST_ROOT}
RUN echo "export PATH=${PATH}" >> /etc/profile
#USER ${USER}
#COPY --chown=${USER} entrypoint.sh ${WORKDIR}
#RUN chmod +x ${WORKDIR}/entrypoint.sh
#ENV PATH=${WORKDIR}:$PATH
ENTRYPOINT ["ngen_partitioner"]
