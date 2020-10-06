FROM alpine:3.12
# In case the main package repositories are down, use the alternative base image:
# FROM gliderlabs/alpine:3.12

ARG REQUIRE="sudo build-base gfortran openssl curl curl-dev tar git m4 zlib-dev libexecinfo-dev"
RUN apk update && apk upgrade \
      && apk add --no-cache ${REQUIRE}


#### INSTALL MPICH ####
# Source is available at http://www.mpich.org/static/downloads/

# Build Options:
# See installation guide of target MPICH version
# Ex: http://www.mpich.org/static/downloads/3.2/mpich-3.2-installguide.pdf
# These options are passed to the steps below
ARG MPICH_VERSION="3.2"
#ARG MPICH_CONFIGURE_OPTIONS="--disable-fortran"
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

#### TEST RUN OF MPI ####
# Hello world example of C and f90 versions
USER root
RUN echo "export PATH=${PATH}" >> /etc/profile
USER ${USER}

# Create a temporary test directory
RUN mkdir -p /tmp/mpich-test
WORKDIR /tmp/mpich-test

# Copy files to the working directory
COPY mpich-test .
ENTRYPOINT ["sh", "/tmp/mpich-test/entrypoint.sh"]
