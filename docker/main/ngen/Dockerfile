################################################################################################################
################################################################################################################
################################################################################################################
##### External Global Args Declaration and Defaults
################################################################################################################
# Any args that will need to be set, first declare them here, then later redeclare them within stage that uses.
# Also, for those with defaults, set those up here so that's easier to find.
ARG DOCKER_INTERNAL_REGISTRY

# Swap or override this as needed (below are the "standard" types from
#   https://cmake.org/cmake/help/latest/manual/cmake-buildsystem.7.html#default-and-custom-configurations)
#ARG NGEN_BUILD_CONFIG_TYPE="Debug"
ARG NGEN_BUILD_CONFIG_TYPE="Release"
#ARG NGEN_BUILD_CONFIG_TYPE="RelWithDebInfo"
#ARG NGEN_BUILD_CONFIG_TYPE="MinSizeRel"

ARG DATASET_DIRECTORIES="config forcing hydrofabric observation output"

# Passing the ARG variables from compose via .env file will squash these defaults with empty strings
# Seems like the work around is to replicate the default values in the build env, or to check for
# empty and set to default as is shown commented out below.
ARG REPO_URL=https://github.com/NOAA-OWP/ngen.git
ARG BRANCH=master
ARG COMMIT
ARG WORKDIR=/ngen

#### Default arguments for required dependencies needed during various build stages
# The Rocky-Linux-based "base" stage, rocky-base
ARG ROCKY_BASE_REQUIRED="sudo openssh openssh-server bash git"
# The Rocky-Linux-based "ngen-deps" stage, rocky-ngen-deps
ARG ROCKY_NGEN_DEPS_REQUIRED="mpich mpich-devel sudo gcc gcc-c++ make cmake tar git gcc-gfortran libgfortran python39 python39-devel python39-pip python39-numpy netcdf netcdf-devel netcdf-cxx4 netcdf-cxx4-devel netcdf-mpich netcdf-mpich-devel netcdf-cxx4-mpich netcdf-cxx4-mpich-devel hdf5 hdf5-devel hdf5-mpich hdf5-mpich-devel bzip2 expat expat-devel flex bison udunits2 udunits2-devel"
# TODO: removed texinfo from list because it couldn't be found; make sure this doesn't lead to issues

ARG BOOST_VERSION=1.72.0
ARG MPICH_VERSION="3.2"
ARG MIN_PYTHON="3.8.0"
ARG MIN_NUMPY="1.18.0"

ARG BUILD_PARALLEL_JOBS

ARG NGEN_ACTIVATE_C="ON"
ARG NGEN_ACTIVATE_FORTRAN="ON"
ARG NGEN_ACTIVATE_PYTHON="ON"
ARG NGEN_MPI_ACTIVE="ON"
ARG NGEN_ROUTING_ACTIVE="ON"
ARG NGEN_UDUNITS_ACTIVE="ON"
ARG NGEN_UDUNITS_QUIET="ON"

ARG BUILD_NOAH_OWP="true"
ARG BUILD_CFE="true"
ARG BUILD_TOPMODEL="true"

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for Rocky-Linux-based "base"
FROM rockylinux:8.5 as rocky-base

ARG USER=mpi
ENV USER=${USER} USER_HOME=/home/${USER}
ENV SSHDIR=${USER_HOME}/.ssh

ARG ROCKY_BASE_REQUIRED

RUN dnf update -y \
    && dnf install -y 'dnf-command(config-manager)' \
    && dnf config-manager --set-enabled powertools \
    && dnf install -y epel-release \
    && dnf -y install ${ROCKY_BASE_REQUIRED} \
    # Note that adduser -p expects an encrypted/hashed password, so it will ignore a simple password \
    && adduser -p 'ignored' ${USER} \
    && echo "${USER}   ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers \
    && chown -R ${USER}:${USER} ${USER_HOME} \
    && cd /etc/ssh/ && ssh-keygen -A -N '' \
    # Config SSH Daemon \
    && sed -i "s/#PasswordAuthentication.*/PasswordAuthentication no/g" /etc/ssh/sshd_config \
    && sed -i "s/#PermitRootLogin.*/PermitRootLogin no/g" /etc/ssh/sshd_config \
    && sed -i "s/#AuthorizedKeysFile/AuthorizedKeysFile/g" /etc/ssh/sshd_config \
    # Unlock non-password USER to enable SSH login \
    #&& passwd -u ${USER} \
    # Set up user's public and private keys \
    && mkdir -p ${SSHDIR} \
    # Default ssh config file that skips (yes/no) question when first login to the host \
    && echo "Host *" > ${SSHDIR}/config \
    && echo "    StrictHostKeyChecking no" >> ${SSHDIR}/config \
    && echo "    TCPKeepAlive yes" >> ${SSHDIR}/config \
    && echo "    ServerAliveCountMax 6" >> ${SSHDIR}/config \
    && echo "    ServerAliveInterval 30" >> ${SSHDIR}/config

USER root

COPY ssh ${SSHDIR}/

ARG WORKDIR

RUN cat ${SSHDIR}/*.pub >> ${SSHDIR}/authorized_keys \
    && chmod -R 600 ${SSHDIR}/* \
    && chown -R ${USER}:${USER} ${SSHDIR} \
    && mkdir -p ${WORKDIR} \
    && chown -R ${USER}:${USER} ${WORKDIR} \
    && echo "cd ${WORKDIR}" >> ${USER_HOME}/.profile \
    && chown ${USER}:${USER} ${USER_HOME}/.profile \
    && cp -a ${USER_HOME}/.profile ${USER_HOME}/.bash_profile

# Switch back to default user when continue the build process
USER ${USER}

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for downloading Boost
FROM rockylinux:8.5 AS download_boost

# Redeclaring inside this stage to get default from before first FROM
ARG BOOST_VERSION

RUN curl -L -o boost_${BOOST_VERSION//./_}.tar.bz2 https://sourceforge.net/projects/boost/files/boost/${BOOST_VERSION}/boost_${BOOST_VERSION//./_}.tar.bz2/download \
    && mkdir /boost \
    && mv boost_${BOOST_VERSION//./_}.tar.bz2 /boost/.

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for Rocky-Linux-based "ngen-deps"
FROM rocky-base as rocky-ngen-deps

ARG BOOST_VERSION
ARG WORKDIR

ENV WORKDIR=${WORKDIR}
ENV BOOST_ROOT=${WORKDIR}/boost

COPY --from=download_boost /boost ${WORKDIR}/boost

ARG MPICH_VERSION
ARG MIN_PYTHON
ARG MIN_NUMPY
ARG ROCKY_NGEN_DEPS_REQUIRED

USER root

ENV HYDRA_HOST_FILE=/etc/opt/hosts

# Hostfile location for mpirun. This file will be updated automatically.
RUN echo "export HYDRA_HOST_FILE=${HYDRA_HOST_FILE}" >> /etc/profile \
    && touch ${HYDRA_HOST_FILE} \
    && chown ${USER}:${USER} ${HYDRA_HOST_FILE} \
    # Install required dependency packages available as RPMs \
    && dnf update -y \
    && dnf install -y ${ROCKY_NGEN_DEPS_REQUIRED} \
    # Install required python dependency packages with Pip \
    && pip3 install numpy pandas pyyaml bmipy netCDF4 \
    # Make aliases for convenience \
    && alias pip='pip3' \
    && echo "alias pip='pip3'" >> /etc/profile \
    && alias python='python3'  \
    && echo "alias python='python3'" >> /etc/profile \
    # Also set up boost here, since we copied the download but only just installed bzip2 to work with it \
    && cd ${BOOST_ROOT} \
    && tar -xjf boost_${BOOST_VERSION//./_}.tar.bz2 \
    && rm boost_${BOOST_VERSION//./_}.tar.bz2

ENV PATH=${PATH}:/usr/lib64/mpich/bin

USER ${USER}

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for building framework in Rocky Linux environment
FROM rocky-base as rocky_init_repo
ARG REPO_URL
ARG BRANCH
ARG COMMIT
ARG WORKDIR

WORKDIR ${WORKDIR}

RUN cd ${WORKDIR} \
    && git clone --single-branch --branch $BRANCH $REPO_URL \
    && cd ./ngen \
    && if [ "x$COMMIT" != "x" ]; then git checkout $COMMIT; fi \
    && git submodule update --init test/googletest \
    && git submodule update --init

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for building framework in Rocky Linux environment
FROM rocky-ngen-deps as rocky_build_ngen

ARG REPO_URL
ARG BRANCH
ARG COMMIT
ARG BUILD_PARALLEL_JOBS

ARG NGEN_BUILD_CONFIG_TYPE
ARG NGEN_ACTIVATE_C
ARG NGEN_ACTIVATE_FORTRAN
ARG NGEN_ACTIVATE_PYTHON
ARG NGEN_MPI_ACTIVE
ARG NGEN_ROUTING_ACTIVE
ARG NGEN_UDUNITS_ACTIVE
ARG NGEN_UDUNITS_QUIET

ARG BUILD_NOAH_OWP
ARG BUILD_CFE
ARG BUILD_TOPMODEL

COPY --chown=${USER} --from=rocky_init_repo ${WORKDIR}/ngen ${WORKDIR}/ngen
ENV BOOST_ROOT=${WORKDIR}/boost

RUN cd ${WORKDIR}/ngen \
    && echo "#!/bin/bash" > build_sub \
    && echo "cmake -B \$1/cmake_build -DCMAKE_BUILD_TYPE=${NGEN_BUILD_CONFIG_TYPE} -S \$1 && cmake --build \$1/cmake_build" >> build_sub \
    && chmod u+x build_sub \
    && if [ "${NGEN_ACTIVATE_PYTHON}" == "ON" ]; then pip3 install -r extern/test_bmi_py/requirements.txt; fi \
    &&  if [ "${NGEN_ACTIVATE_FORTRAN}" == "ON" ]; then \
                ./build_sub extern/iso_c_fortran_bmi; \
                if [ "${BUILD_NOAH_OWP}" == "true" ] ; then ./build_sub extern/noah-owp-modular; fi; \
        fi \
    &&  if [ "${NGEN_ACTIVATE_C}" == "ON" ]; then \
                if [ "${BUILD_CFE}" == "true" ] ; then ./build_sub extern/cfe; fi; \
                if [ "${BUILD_TOPMODEL}" == "true" ] ; then ./build_sub extern/topmodel; fi; \
        fi \
    && cmake -B cmake_build -S . \
            -DMPI_ACTIVE:BOOL=${NGEN_MPI_ACTIVE} \
            -DBMI_C_LIB_ACTIVE:BOOL=${NGEN_ACTIVATE_C} \
            -DBMI_FORTRAN_ACTIVE:BOOL=${NGEN_ACTIVATE_FORTRAN} \
            -DNGEN_ACTIVATE_PYTHON:BOOL=${NGEN_ACTIVATE_PYTHON} \
            -DNGEN_ACTIVATE_ROUTING:BOOL=${NGEN_ROUTING_ACTIVE} \
            -DUDUNITS_ACTIVE:BOOL=${NGEN_UDUNITS_ACTIVE} \
            -DUDUNITS_QUIET:BOOL=${NGEN_UDUNITS_QUIET} \
            -DCMAKE_INSTALL_PREFIX=${WORKDIR} \
    && cmake --build cmake_build -j ${BUILD_PARALLEL_JOBS} \
    #Run the tests, if they fail, the image build fails \
    && cmake_build/test/test_unit \
    &&  if [ "${NGEN_ACTIVATE_C}" == "ON" ]; then \
            ./build_sub extern/test_bmi_c; \
            cmake_build/test/test_bmi_c; \
        fi \
    &&  if [ "${NGEN_ACTIVATE_FORTRAN}" == "ON" ]; then \
            ./build_sub extern/test_bmi_fortran; \
            cmake_build/test/test_bmi_fortran; \
        fi \
    &&  if [ "${NGEN_ACTIVATE_PYTHON}" == "ON" ]; then \
            cmake_build/test/test_bmi_python; \
        fi \
    &&  if [ "${NGEN_ACTIVATE_C}" == "ON" ] && [ "${NGEN_ACTIVATE_FORTRAN}" == "ON" ] && [ "${NGEN_ACTIVATE_PYTHON}" == "ON" ]; then \
            cmake_build/test/test_bmi_multi; \
        fi

################################################################################################################
################################################################################################################
##### Final stage for image
FROM rocky_build_ngen

#RUN cd ./ngen && mkdir ${WORKDIR}/bin && cp cmake_build/ngen ${WORKDIR}/bin && cp -r data ${WORKDIR}/data \
#    && cd $WORKDIR && rm -rf ngen boost

USER root
# Remove the boost headers now that ngen is compiled; also update path and make sure dataset directory is there
RUN rm -rf ${BOOST_ROOT} && echo "export PATH=${PATH}" >> /etc/profile \
    && sed -i "s/PasswordAuthentication yes/#PasswordAuthentication yes/g" /etc/ssh/sshd_config \
    && sed -i "s/PermitRootLogin yes/PermitRootLogin no/g" /etc/ssh/sshd_config \
    && sed -i "s/#ClientAliveInterval.*/ClientAliveInterval 60/" /etc/ssh/sshd_config \
    && sed -i "s/#ClientAliveCountMax.*/ClientAliveCountMax 5/" /etc/ssh/sshd_config \
    && rm /var/run/nologin  \
    && mkdir -p /dmod/datasets && chown ${USER} /dmod/datasets \
    && mkdir -p /dmod/shared_libs && chown ${USER} /dmod/shared_libs
USER ${USER}

COPY --chown=${USER} entrypoint.sh ${WORKDIR}

ENV HYDRA_PROXY_RETRY_COUNT=5

# Change permissions for entrypoint and make sure dataset volume mount parent directories exists
RUN chmod +x ${WORKDIR}/entrypoint.sh \
    && for d in ${DATASET_DIRECTORIES}; do mkdir -p /dmod/datasets/${d}; done \
    && for d in noah-owp-modular topmodel cfe; do if [ -d ngen/extern/${d}/cmake_build ]; then cp -a ngen/extern/${d}/cmake_build/*.so.*; cp -L -l -p ngen/extern/${d}/cmake_build/*.so /dmod/shared_libs/.; fi; done

WORKDIR ${WORKDIR}
ENV PATH=${WORKDIR}:$PATH
ENTRYPOINT ["entrypoint.sh"]
CMD [""]
