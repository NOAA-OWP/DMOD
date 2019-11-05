FROM 127.0.0.1:5000/nwm-base
# In case the main package repositories are down, use the alternative base image:
# FROM gliderlabs/alpine:3.4
USER root
ARG REPOS="http://dl-cdn.alpinelinux.org/alpine/edge/testing"
# Building hdf5 from source for parallel support, otherwise add hdf5 hdf5-dev to the list below
ARG REQUIRE="sudo build-base gfortran openssl curl curl-dev tar git m4 zlib-dev"
RUN apk update && apk upgrade \
      && apk add --repository ${REPOS} --no-cache ${REQUIRE} 

#### INSTALL MPICH ####
# Source is available at http://www.mpich.org/static/downloads/

# Build Options:
# See installation guide of target MPICH version
# Ex: http://www.mpich.org/static/downloads/3.2/mpich-3.2-installguide.pdf
# These options are passed to the steps below
ARG MPICH_VERSION="3.2"
ARG MPICH_CONFIGURE_OPTIONS=""
ARG MPICH_MAKE_OPTIONS

# Download, build, and install MPICH
RUN mkdir /tmp/mpich-src
WORKDIR /tmp/mpich-src
RUN wget http://www.mpich.org/static/downloads/${MPICH_VERSION}/mpich-${MPICH_VERSION}.tar.gz \
      && tar xfz mpich-${MPICH_VERSION}.tar.gz  \
      && cd mpich-${MPICH_VERSION}  \
      && ./configure ${MPICH_CONFIGURE_OPTIONS}  \
      && make ${MPICH_MAKE_OPTIONS} && make install \
      && rm -rf /tmp/mpich-src

#### TEST MPICH INSTALLATION ####
RUN mkdir /tmp/mpich-test
WORKDIR /tmp/mpich-test
# FIXME clean up mpich-test, can include a test or can simply ignore
#COPY mpich-test .
#RUN sh test.sh
#RUN rm -rf /tmp/mpich-test

WORKDIR /tmp
####
#   Additional software dependencies source builds
####
# Build HDF5
RUN wget https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.10/hdf5-1.10.4/src/hdf5-1.10.4.tar.gz \
    && tar -xzf hdf5-1.10.4.tar.gz \
    && cd hdf5-1.10.4 \
    && ./configure --enable-parallel --prefix=/usr \
    && make && make install
# Get the latest netCDF C code from unidata github
RUN curl -s https://api.github.com/repos/Unidata/netcdf-c/releases/latest \
    | grep "tarball_url" \
    | cut -d '"' -f 4 \
    | sudo xargs wget -O netcdf-latest.tar.gz
RUN mkdir netcdf
RUN tar -xzf netcdf-latest.tar.gz -C netcdf --strip 1
WORKDIR /tmp/netcdf
## NOT SURE WHY THESE ALL REQUIRE SUDO...
# RUN LIBS=curl sudo CPPFLAGS=-I/usr/local/include ./configure --prefix=/usr
# RUN sudo make
# RUN sudo make install
## FIXME this seems unique to the docker play ground environment...
RUN LIBS=curl CPPFLAGS=-I/usr/local/include ./configure --prefix=/usr
RUN make
RUN make install

WORKDIR /tmp
# Get the latest netCDF fortran release from unidata github
RUN curl -s https://api.github.com/repos/Unidata/netcdf-fortran/releases/latest \
    | grep "tarball_url" \
    | cut -d '"' -f 4 \
    | sudo xargs wget -O netcdf-fortran-latest.tar.gz
RUN mkdir netcdf-fortran
# extract this releast to netcdf-fortran
RUN tar -xzf netcdf-fortran-latest.tar.gz -C netcdf-fortran --strip 1
WORKDIR netcdf-fortran
# FIXME WHY DO THESE NOT NEED SUDO...so weird
RUN ./configure --prefix=/usr
RUN make
# RUN sudo make install
RUN make install

#### CLEAN UP ####
WORKDIR /
RUN rm -rf /tmp/*

####
#   Configure MPI
####

#Hostfile location for mpirun. This file will be updated automatically.
ENV HYDRA_HOST_FILE /etc/opt/hosts
RUN echo "export HYDRA_HOST_FILE=${HYDRA_HOST_FILE}" >> /etc/profile

RUN touch ${HYDRA_HOST_FILE}
RUN chown ${USER}:${USER} ${HYDRA_HOST_FILE}
USER ${USER}
####
#   Pull latest NWM and build
####
RUN mkdir -p /nwm/domains
WORKDIR /nwm
