################################################################################################################
################################################################################################################
##### Get our already-built numpy wheel
ARG DOCKER_INTERNAL_REGISTRY
FROM ${DOCKER_INTERNAL_REGISTRY}/dmod-py-deps as deps-sources

################################################################################################################
FROM ${DOCKER_INTERNAL_REGISTRY}/nwm-base

USER root

########################################
# Model specific ENV
########################################
ARG WORKDIR=/ngen
ENV WORKDIR=${WORKDIR}
#### CREATE WORKING DIRECTORY FOR MODEL #### \
RUN mkdir ${WORKDIR} \
    && chown -R ${USER}:${USER} ${WORKDIR} \
    # Auto go to default working directory when user ssh login \
    && echo "cd $WORKDIR" >> ${USER_HOME}/.profile \
WORKDIR ${WORKDIR}

########################################
# Model specific dependencies/builds
########################################

#ARG REPOS="http://dl-cdn.alpinelinux.org/alpine/edge/testing"
ARG REQUIRE="sudo gcc g++ musl-dev make cmake tar git"

#Eventually, MPI probably required for ngen
ENV HYDRA_HOST_FILE /etc/opt/hosts
# MPICH Build Options:
# See installation guide of target MPICH version
# Ex: http://www.mpich.org/static/downloads/3.2/mpich-3.2-installguide.pdf
# These options are passed to the steps below
ARG MPICH_VERSION="3.2"
ARG MPICH_CONFIGURE_OPTIONS="--disable-fortran"
ARG MPICH_MAKE_OPTIONS

### INSTALL MPICH ####
# Source is available at http://www.mpich.org/static/downloads/
# Download, build, and install MPICH

RUN apk update && apk upgrade && apk add --repository ${REPOS} --no-cache ${REQUIRE}

    ####
    # MPICH build and install
    #### 
RUN mkdir /tmp/mpich-src \
    && cd /tmp/mpich-src \
    && wget http://www.mpich.org/static/downloads/${MPICH_VERSION}/mpich-${MPICH_VERSION}.tar.gz \
    && tar xfz mpich-${MPICH_VERSION}.tar.gz

RUN cd /tmp/mpich-src/mpich-${MPICH_VERSION} && ./configure ${MPICH_CONFIGURE_OPTIONS} 
RUN cd /tmp/mpich-src/mpich-${MPICH_VERSION} && make -j 4 ${MPICH_MAKE_OPTIONS} && make install

RUN cd /tmp && rm -rf /tmp/mpich-src

    #### 
    #   Configure MPI
    #### 
    # Hostfile location for mpirun. This file will be updated automatically.
RUN echo "export HYDRA_HOST_FILE=${HYDRA_HOST_FILE}" >> /etc/profile \
    && touch ${HYDRA_HOST_FILE} \
    && chown ${USER}:${USER} ${HYDRA_HOST_FILE} \
    && mkdir -p ${WORKDIR}/domains


RUN apk add --repository ${REPOS} python3 python3-dev libstdc++ py3-pip
COPY --from=deps-sources /DIST/numpy*.whl /wheel_dist/.

USER ${USER}
####
#   Pull latest ngen and build
####
WORKDIR ${WORKDIR}

ARG BOOST_VERSION=1.72.0
ENV BOOST_ROOT=${WORKDIR}/boost

#RUN wget https://dl.bintray.com/boostorg/release/${BOOST_VERSION}/source/boost_${BOOST_VERSION//./_}.tar.gz \
RUN wget https://sourceforge.net/projects/boost/files/boost/${BOOST_VERSION}/boost_${BOOST_VERSION//./_}.tar.gz/download -O boost_${BOOST_VERSION//./_}.tar.gz \
#### \
    # Get boost headers \
    #### \
    && mkdir -p ${WORKDIR}/boost \
    && tar zxf boost_${BOOST_VERSION//./_}.tar.gz -C ./boost --strip-components=1 \
    && rm boost_${BOOST_VERSION//./_}.tar.gz

USER root
RUN rm /wheel_dist && mkdir /wheel_dist
COPY --from=deps-sources /DIST/numpy*.whl /wheel_dist/.
USER ${USER}