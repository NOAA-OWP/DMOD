ARG DOCKER_INTERNAL_REGISTRY
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

USER ${USER}
####
#   Pull latest ngen and build
####
WORKDIR ${WORKDIR}
