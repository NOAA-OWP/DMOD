ARG NETCDF_C_VERSION
ARG DOCKER_INTERNAL_REGISTRY
FROM ${DOCKER_INTERNAL_REGISTRY}/nwm-base
# In case the main package repositories are down, use the alternative base image:
# FROM gliderlabs/alpine:3.4

USER root

########################################
# Model specific ENV
########################################
ARG WORKDIR=/nwm
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

ARG REPOS="http://dl-cdn.alpinelinux.org/alpine/edge/testing"
# Building hdf5 from source for parallel support, otherwise add hdf5 hdf5-dev to the list below
ARG REQUIRE="sudo build-base gfortran openssl curl curl-dev tar git m4 zlib-dev libexecinfo-dev"

# ARG NETCDF_C_VERSION="latest"
#ARG NETCDF_C_VERSION="v4.6.0"
ARG NETCDF_C_VERSION
ENV NETCDF_C_VERSION ${NETCDF_C_VERSION:-latest}
ENV HYDRA_HOST_FILE /etc/opt/hosts
# MPICH Build Options:
# See installation guide of target MPICH version
# Ex: http://www.mpich.org/static/downloads/3.2/mpich-3.2-installguide.pdf
# These options are passed to the steps below
ARG MPICH_VERSION="3.2"
ARG MPICH_CONFIGURE_OPTIONS=""
ARG MPICH_MAKE_OPTIONS

### INSTALL MPICH ####
# Source is available at http://www.mpich.org/static/downloads/
# Download, build, and install MPICH

RUN apk update && apk upgrade && apk add --repository ${REPOS} --no-cache ${REQUIRE} \
    && mkdir /tmp/mpich-src \
    && cd /tmp/mpich-src \
    && wget http://www.mpich.org/static/downloads/${MPICH_VERSION}/mpich-${MPICH_VERSION}.tar.gz \
    && tar xfz mpich-${MPICH_VERSION}.tar.gz  \
    && cd mpich-${MPICH_VERSION}  \
    && ./configure ${MPICH_CONFIGURE_OPTIONS}  \
    && make -j 8 ${MPICH_MAKE_OPTIONS} && make install \
    && cd /tmp \
    && rm -rf /tmp/mpich-src \
    #### \
    #   Additional software dependencies source builds \
    #### \
    # Build HDF5 \
    && wget https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.10/hdf5-1.10.4/src/hdf5-1.10.4.tar.gz \
    && tar -xzf hdf5-1.10.4.tar.gz \
    && cd hdf5-1.10.4 \
    && ./configure --enable-parallel --prefix=/usr \
    && make -j 8 && make install \
    && cd /tmp \
    # Get netCDF C code from unidata github \
    # The NETCDF_C_VERSION Dockerfile arg may be supplied with a valid version if desired; otherwise latest is used \
    # Currently 4.6 needs to be used, until there is a patch available for a known bug that causes issues with 4.7/latest \
    && if [[ "${NETCDF_C_VERSION}" == "latest" ]]; then \
            curl -s https://api.github.com/repos/Unidata/netcdf-c/releases/latest \
                | grep "tarball_url" \
                | cut -d '"' -f 4 \
                | sudo xargs wget -O netcdf-latest.tar.gz ; \
        else \
            curl -s https://api.github.com/repos/Unidata/netcdf-c/releases \
                | grep "tarball_url" \
                | grep "${NETCDF_C_VERSION}" \
                | cut -d '"' -f 4 \
                | sudo xargs wget -O netcdf-${NETCDF_C_VERSION}.tar.gz ; \
        fi \
    && mkdir netcdf \
    && tar -xzf netcdf-${NETCDF_C_VERSION}.tar.gz -C netcdf --strip 1 \
    && cd /tmp/netcdf \
    && LIBS=curl && ./configure CPPFLAGS=-I/usr/local/include --prefix=/usr \
    && make -j 8 && make install \
    && cd /tmp \
    && curl -s https://api.github.com/repos/Unidata/netcdf-fortran/releases/latest \
           | grep "tarball_url" \
           | cut -d '"' -f 4 \
           | sudo xargs wget -O netcdf-fortran-latest.tar.gz \
    && mkdir netcdf-fortran \
    && tar -xzf netcdf-fortran-latest.tar.gz -C netcdf-fortran --strip 1 \
    && cd netcdf-fortran \
    && FC=mpif90 ./configure --prefix=/usr \
    && make -j 8 && make install \
    && cd / \
    && rm -rf /tmp/* \
    #### \
    #   Configure MPI \
    #### \
    # Hostfile location for mpirun. This file will be updated automatically. \
    && echo "export HYDRA_HOST_FILE=${HYDRA_HOST_FILE}" >> /etc/profile \
    && touch ${HYDRA_HOST_FILE} \
    && chown ${USER}:${USER} ${HYDRA_HOST_FILE} \
    && mkdir -p ${WORKDIR}/domains

USER ${USER}
####
#   Pull latest NWM and build
####
WORKDIR ${WORKDIR}
