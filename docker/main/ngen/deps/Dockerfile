ARG DOCKER_INTERNAL_REGISTRY
ARG BOOST_VERSION=1.72.0
ARG MPICH_VERSION="3.2"
ARG MIN_PYTHON="3.8.0"
ARG MIN_NUMPY="1.18.0"
#ARG REPOS="http://dl-cdn.alpinelinux.org/alpine/edge/testing"
ARG REPOS=""

################################################################################################################
FROM ${DOCKER_INTERNAL_REGISTRY}/nwm-base AS get_boost

# Redeclaring inside this stage to get default from before first FROM
ARG BOOST_VERSION

USER root

RUN wget https://sourceforge.net/projects/boost/files/boost/${BOOST_VERSION}/boost_${BOOST_VERSION//./_}.tar.bz2/download -O boost_${BOOST_VERSION//./_}.tar.bz2 \
    && mkdir /boost \
    && mv boost_${BOOST_VERSION//./_}.tar.bz2 /boost/. \
    && cd /boost \
    && tar -xjf boost_${BOOST_VERSION//./_}.tar.bz2 \
    && rm boost_${BOOST_VERSION//./_}.tar.bz2

USER ${USER}
################################################################################################################
FROM ${DOCKER_INTERNAL_REGISTRY}/nwm-base AS download_mpi

# Redeclaring inside this stage to get default from before first FROM
ARG MPICH_VERSION

USER root

# MPICH build and install \
    #### \
RUN mkdir /mpich-src \
    && cd /mpich-src \
    && wget http://www.mpich.org/static/downloads/${MPICH_VERSION}/mpich-${MPICH_VERSION}.tar.gz \
    && tar xfz mpich-${MPICH_VERSION}.tar.gz \
    && rm mpich-${MPICH_VERSION}.tar.gz

USER ${USER}
################################################################################################################
FROM ${DOCKER_INTERNAL_REGISTRY}/nwm-base AS install_apk_deps
USER root

# Redeclaring inside this stage to get default from before first FROM
ARG REPOS

ARG MPI_REQUIRE="sudo gcc g++ musl-dev make cmake tar git"

RUN apk update && apk upgrade \
    && if [ -n "${REPOS}" ]; then \
            apk add --repository ${REPOS} --no-cache ${MPI_REQUIRE}; \
        else \
            apk add --no-cache ${MPI_REQUIRE}; \
        fi

USER ${USER}
################################################################################################################
FROM install_apk_deps

USER root

# Redeclaring inside this stage to get default from before first FROM
ARG MIN_PYTHON
ARG MIN_NUMPY
ARG MPICH_VERSION
ARG REPOS

ARG WORKDIR=/ngen
ENV WORKDIR=${WORKDIR}

ENV BOOST_ROOT=${WORKDIR}/boost

ENV HYDRA_HOST_FILE /etc/opt/hosts

ARG MPICH_CONFIGURE_OPTIONS="--disable-fortran"
ARG MPICH_MAKE_OPTIONS

# Copying should also take care of creating the working dir
COPY --from=get_boost /boost ${WORKDIR}/boost
COPY --from=download_mpi /mpich-src ${WORKDIR}/mpich-src

# See installation guide of target MPICH version
# Ex: http://www.mpich.org/static/downloads/3.2/mpich-3.2-installguide.pdf
# These options are passed to the steps below

#RUN mkdir ${WORKDIR}
# Auto go to default working directory when user ssh login
RUN echo "cd ${WORKDIR}" >> ${USER_HOME}/.profile \
    && cd ${WORKDIR}/mpich-src/mpich-${MPICH_VERSION} \
    && ./configure ${MPICH_CONFIGURE_OPTIONS}  \
    && make -j $(nproc) ${MPICH_MAKE_OPTIONS} \
    && make install \
    && cd ${WORKDIR} \
    && rm -rf ${WORKDIR}/mpich-src \
    && chown -R ${USER}:${USER} ${WORKDIR} \
    #### \
    #   Configure MPI \
    #### \
    # Hostfile location for mpirun. This file will be updated automatically. \
    && echo "export HYDRA_HOST_FILE=${HYDRA_HOST_FILE}" >> /etc/profile \
    && touch ${HYDRA_HOST_FILE} \
    && chown ${USER}:${USER} ${HYDRA_HOST_FILE}
    #&& mkdir -p ${WORKDIR}/domains

# Handle final required dependencies separately so we don't have to, e.g., rebuild MPI if we want to update Python
# Also include (not quite authoritative) pip packages required for the test Python BMI library
ARG REQUIRE="sudo gcc g++ musl-dev make cmake tar git gfortran libgfortran python3>=${MIN_PYTHON} python3-dev>=${MIN_PYTHON} py3-pip py3-numpy>=${MIN_NUMPY} py3-numpy-dev>=${MIN_NUMPY} py3-pandas netcdf netcdf-dev hdf5 hdf5-dev bzip2 texinfo expat expat-dev flex bison"
RUN apk update && apk upgrade \
    && if [ -n "${REPOS}" ]; then \
            apk add --repository ${REPOS} --no-cache ${REQUIRE}; \
        else \
            apk add --no-cache ${REQUIRE}; \
        fi \
    && pip install numpy pandas pyyaml bmipy netCDF4

ENV BOOST_ROOT=${WORKDIR}/boost
USER ${USER}
WORKDIR ${WORKDIR}
