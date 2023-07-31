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

ARG TROUTE_REPO_URL=https://github.com/NOAA-OWP/t-route.git
ARG TROUTE_BRANCH=ngen
ARG TROUTE_COMMIT

#### Default arguments for required dependencies needed during various build stages
# The Rocky-Linux-based "base" stage, rocky-base
ARG ROCKY_BASE_REQUIRED="sudo openssh openssh-server bash git"
# The Rocky-Linux-based "ngen-deps" stage, rocky-ngen-deps
# TODO: later look at separating build and run images again, and install static lib netcdf packages in run images
#ARG ROCKY_NGEN_DEPS_REQUIRED="mpich mpich-devel sudo gcc gcc-c++ make cmake tar git gcc-gfortran libgfortran \
#    python39 python39-devel python39-pip python39-numpy \
#    netcdf-cxx4-devel netcdf-cxx4-mpich-devel netcdf-fortran-devel netcdf-fortran-mpich-devel \
#    hdf5 hdf5-devel hdf5-mpich hdf5-mpich-devel \
#    bzip2 expat expat-devel flex bison udunits2 udunits2-devel"

ARG ROCKY_NGEN_DEPS_REQUIRED="sudo gcc gcc-c++ make cmake tar git gcc-gfortran libgfortran \
    python39 python39-devel python39-pip \
    bzip2 expat expat-devel flex bison udunits2 udunits2-devel zlib-devel"
# TODO: removed texinfo from list because it couldn't be found; make sure this doesn't lead to issues

ARG BOOST_VERSION=1.72.0
ARG MPICH_VERSION="3.2"
ARG MIN_PYTHON="3.8.0"
ARG MIN_NUMPY="1.18.0"
ARG BLOSC2_VERSION

ARG NETCDF_C_VERSION=4.8.1
ARG NETCDF_CXX_VERSION=4.3.1
ARG NETCDF_FORTRAN_VERSION=4.6.0
ARG HD5_VERSION=1.10.9

# Work around Fortran MPI issue
ARG FCFLAGS="-w -fallow-argument-mismatch -O2"
ARG FFLAGS="-w -fallow-argument-mismatch -O2"
ARG MPICH_CONFIGURE_OPTIONS=""
ARG MPICH_MAKE_OPTIONS

ARG BUILD_PARALLEL_JOBS

ARG NGEN_ACTIVATE_C="ON"
ARG NGEN_ACTIVATE_FORTRAN="ON"
ARG NGEN_ACTIVATE_PYTHON="ON"
ARG NGEN_NETCDF_ACTIVE="ON"
ARG NGEN_ROUTING_ACTIVE="ON"
ARG NGEN_UDUNITS_ACTIVE="ON"
ARG NGEN_UDUNITS_QUIET="ON"

ARG BUILD_NGEN_SERIAL="true"
ARG BUILD_NGEN_PARALLEL="true"
ARG BUILD_PARTITIONER="false"
ARG BUILD_NOAH_OWP="true"
ARG BUILD_CFE="true"
ARG BUILD_TOPMODEL="true"
ARG BUILD_PET="true"
ARG BUILD_SLOTH="true"

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
##### Create intermediate Docker build stage for downloading MPICH
FROM rockylinux:8.5 AS download_mpich

# Redeclaring inside this stage to get default from before first FROM
ARG MPICH_VERSION

RUN curl -o /tmp/mpich-${MPICH_VERSION}.tar.gz https://www.mpich.org/static/downloads/${MPICH_VERSION}/mpich-${MPICH_VERSION}.tar.gz


################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for downloading MPICH
FROM rockylinux:8.5 AS download_hd5

# Redeclaring inside this stage to get default from before first FROM
ARG HD5_VERSION

RUN curl -o /tmp/hdf5-${HD5_VERSION}.tar.gz https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.10/hdf5-${HD5_VERSION}/src/hdf5-${HD5_VERSION}.tar.gz

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for downloading netcdf
FROM rocky-base AS download_netcdf

# Redeclaring inside this stage to get default from before first FROM
ARG NETCDF_C_VERSION

RUN if [[ "${NETCDF_C_VERSION}" == "latest" ]]; then \
            curl -s https://api.github.com/repos/Unidata/netcdf-c/releases/latest \
                | grep "tarball_url" \
                | cut -d '"' -f 4 \
                | xargs curl -L -o /tmp/netcdf-${NETCDF_C_VERSION}.tar.gz ; \
        else \
            curl -s https://api.github.com/repos/Unidata/netcdf-c/releases \
                | grep "tarball_url" \
                | grep "${NETCDF_C_VERSION}" \
                | cut -d '"' -f 4 \
                | xargs curl -L -o /tmp/netcdf-${NETCDF_C_VERSION}.tar.gz ; \
        #fi \
        #&& mkdir /tmp/netcdf \
        #&& tar -xzf /tmp/netcdf-${NETCDF_C_VERSION}.tar.gz -C /tmp/netcdf --strip 1 \
        #&& rm /tmp/netcdf-${NETCDF_C_VERSION}.tar.gz
        fi

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for downloading netcdf-fortran
FROM rocky-base AS download_netcdf_fortran

# Redeclaring inside this stage to get default from before first FROM
ARG NETCDF_FORTRAN_VERSION

RUN if [[ "${NETCDF_FORTRAN_VERSION}" == "latest" ]]; then \
            curl -s https://api.github.com/repos/Unidata/netcdf-fortran/releases/latest \
                | grep "tarball_url" \
                | cut -d '"' -f 4 \
                | xargs curl -L -o /tmp/netcdf-fortran-${NETCDF_FORTRAN_VERSION}.tar.gz ; \
        else \
            curl -s https://api.github.com/repos/Unidata/netcdf-fortran/releases \
                | grep "tarball_url" \
                | grep "${NETCDF_FORTRAN_VERSION}" \
                | cut -d '"' -f 4 \
                | xargs curl -L -o /tmp/netcdf-fortran-${NETCDF_FORTRAN_VERSION}.tar.gz ; \
        #fi \
        #&& mkdir /tmp/netcdf-fortran \
        #&& tar -xzf /tmp/netcdf-fortran-${NETCDF_FORTRAN_VERSION}.tar.gz -C /tmp/netcdf-fortran --strip 1 \
        #&& rm /tmp/netcdf-fortran-${NETCDF_FORTRAN_VERSION}.tar.gz
        fi

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for downloading NetCDF C++
FROM rocky-base AS download_netcdf_cxx

# Redeclaring inside this stage to get default from before first FROM
ARG NETCDF_CXX_VERSION

RUN if [[ "${NETCDF_CXX_VERSION}" == "latest" ]]; then \
            curl -s https://api.github.com/repos/Unidata/netcdf-cxx4/releases/latest \
                | grep "tarball_url" \
                | cut -d '"' -f 4 \
                | xargs curl -L -o /tmp/netcdf-cxx4-${NETCDF_CXX_VERSION}.tar.gz ; \
        else \
            curl -s https://api.github.com/repos/Unidata/netcdf-cxx4/releases \
                | grep "tarball_url" \
                | grep "${NETCDF_CXX_VERSION}" \
                | cut -d '"' -f 4 \
                | xargs curl -L -o /tmp/netcdf-cxx4-${NETCDF_CXX_VERSION}.tar.gz ; \
        #fi \
        #&& mkdir /tmp/netcdf-cxx4 \
        #&& tar -xzf /tmp/netcdf-cxx4-${NETCDF_CXX_VERSION}.tar.gz -C /tmp/netcdf-cxx4 --strip 1 \
        #&& rm /tmp/netcdf-cxx4-${NETCDF_CXX_VERSION}.tar.gz
        fi
    # This URL might also work for the analogous version:
    #   https://downloads.unidata.ucar.edu/netcdf-cxx/4.3.1/netcdf-cxx4-4.3.1.tar.gz
################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for just prior to "ngen-deps" for installing packaged deps
FROM rocky-base as rocky-ngen-packaged-deps

ARG ROCKY_NGEN_DEPS_REQUIRED

# Note that this includes numpy, which is needed for Python BMI support, regardless of BMI module 
USER root
RUN dnf update -y && dnf install -y ${ROCKY_NGEN_DEPS_REQUIRED} \
    && pip3 install --upgrade pip \
    && if [ "${NGEN_ACTIVATE_PYTHON}" == "ON" ]; then pip3 install numpy; fi
USER ${USER}

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for Rocky-Linux-based "ngen-deps"
FROM rocky-ngen-packaged-deps as rocky-ngen-deps

ARG BOOST_VERSION
ARG WORKDIR

ENV WORKDIR=${WORKDIR}
ENV BOOST_ROOT=${WORKDIR}/boost

COPY --from=download_boost /boost ${WORKDIR}/boost

ARG MPICH_VERSION
ARG MIN_PYTHON
ARG MIN_NUMPY
ARG BLOSC2_VERSION
ARG ROCKY_NGEN_DEPS_REQUIRED

ARG MPICH_CONFIGURE_OPTIONS
ARG MPICH_MAKE_OPTIONS
ARG HD5_VERSION
ARG NETCDF_C_VERSION
ARG NETCDF_CXX_VERSION
ARG NETCDF_FORTRAN_VERSION

ENV MPICH_CONFIGURE_OPTIONS=${MPICH_CONFIGURE_OPTIONS}
ENV MPICH_MAKE_OPTIONS=${MPICH_MAKE_OPTIONS}
ENV HD5_VERSION=${HD5_VERSION}
ENV NETCDF_C_VERSION=${NETCDF_C_VERSION}
ENV NETCDF_CXX_VERSION=${NETCDF_CXX_VERSION}
ENV NETCDF_FORTRAN_VERSION=${NETCDF_FORTRAN_VERSION}

COPY --from=download_mpich /tmp/mpich-${MPICH_VERSION}.tar.gz /tmp/ngen-deps/mpich-${MPICH_VERSION}.tar.gz
COPY --from=download_hd5 /tmp/hdf5-${HD5_VERSION}.tar.gz /tmp/ngen-deps/hdf5-${HD5_VERSION}.tar.gz
COPY --from=download_netcdf /tmp/netcdf-${NETCDF_C_VERSION}.tar.gz /tmp/ngen-deps/netcdf-${NETCDF_C_VERSION}.tar.gz
COPY --from=download_netcdf_cxx /tmp/netcdf-cxx4-${NETCDF_CXX_VERSION}.tar.gz /tmp/ngen-deps/netcdf-cxx4-${NETCDF_CXX_VERSION}.tar.gz
COPY --from=download_netcdf_fortran /tmp/netcdf-fortran-${NETCDF_FORTRAN_VERSION}.tar.gz /tmp/ngen-deps/netcdf-fortran-${NETCDF_FORTRAN_VERSION}.tar.gz

USER root

ENV HYDRA_HOST_FILE=/etc/opt/hosts

# Hostfile location for mpirun. This file will be updated automatically.
RUN echo "export HYDRA_HOST_FILE=${HYDRA_HOST_FILE}" >> /etc/profile \
    && touch ${HYDRA_HOST_FILE} \
    && chown ${USER}:${USER} ${HYDRA_HOST_FILE} \
    ################### Build and install dependencies from source ################### \
    ##### Prep temp build root directory \
    && mkdir -p /tmp/ngen-deps \
    ##### Build and install mpich \
    && cd /tmp/ngen-deps \
    && tar xfz mpich-${MPICH_VERSION}.tar.gz  \
    && cd mpich-${MPICH_VERSION} \
    && ./configure ${MPICH_CONFIGURE_OPTIONS} \
    && make -j $(nproc) ${MPICH_MAKE_OPTIONS} && make install \
    ##### Build and install HDF5 \
    && cd /tmp/ngen-deps \
    && tar -xzf hdf5-${HD5_VERSION}.tar.gz \
    && cd hdf5-${HD5_VERSION} \
    && ./configure --enable-parallel --prefix=/usr \
    && make -j $(nproc) && make install \
    ##### Build and install NetCDF C \
    && cd /tmp/ngen-deps \
    && mkdir netcdf \
    && tar -xzf netcdf-${NETCDF_C_VERSION}.tar.gz -C netcdf --strip 1 \
    && cd netcdf \
    && LIBS=curl && ./configure --prefix=/usr \
    && make -j $(nproc) && make install \
    # TODO: if we run into any problem, might need to reactivate this \
    #&& make check \
    ##### Build and install NetCDF Fortran \
    && cd /tmp/ngen-deps \
    && mkdir netcdf-fortran \
    && tar -xzf netcdf-fortran-${NETCDF_FORTRAN_VERSION}.tar.gz -C netcdf-fortran --strip 1 \
    && cd netcdf-fortran \
    && export NCDIR=/usr NFDIR=/usr \
    && LD_LIBRARY_PATH=/usr/lib CPPFLAGS=-I/usr/include LDFLAGS=-L/usr/lib ./configure --prefix=/usr \
    && make -j $(nproc) && make install \
    ##### Build and install NetCDF C++ \
    && cd /tmp/ngen-deps \
    && mkdir netcdf-cxx4 \
    && tar -xzf netcdf-cxx4-${NETCDF_CXX_VERSION}.tar.gz -C netcdf-cxx4 --strip 1 \
    && mkdir netcdf-cxx4/build \
    && cd netcdf-cxx4/build \
    && cmake .. \
    && make \
    # TODO: if we run into any problem, might need to reactivate this \
    # && ctest \
    && make install \
    # Install required python dependency packages with Pip \
    && pip3 install numpy pandas pyyaml bmipy Cython blosc2==${BLOSC2_VERSION:-2.0.0} netCDF4 wheel packaging \
    && env HDF5_DIR=/usr pip3 install --no-build-isolation tables \
    # Make aliases for convenience \
    && alias pip='pip3' \
    && echo "alias pip='pip3'" >> /etc/profile \
    && alias python='python3'  \
    && echo "alias python='python3'" >> /etc/profile \
    # Also set up boost here, since we copied the download but only just installed bzip2 to work with it \
    && cd ${BOOST_ROOT} \
    && tar -xjf boost_${BOOST_VERSION//./_}.tar.bz2 \
    && rm boost_${BOOST_VERSION//./_}.tar.bz2 \
    && rm -rf /tmp/ngen-deps

ENV PATH=${PATH}:/usr/lib64/mpich/bin
ENV LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/lib:/usr/local/lib64

USER ${USER}

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for building t-route in Rocky Linux environment
FROM rocky-base as rocky_init_troute_repo
ARG TROUTE_REPO_URL
ARG TROUTE_BRANCH
ARG TROUTE_COMMIT
ARG WORKDIR

WORKDIR ${WORKDIR}

RUN cd ${WORKDIR} \
    && git clone --single-branch --branch $TROUTE_BRANCH $TROUTE_REPO_URL \
    && cd ./t-route \
    && if [ "x$TROUTE_COMMIT" != "x" ]; then git checkout $TROUTE_COMMIT; fi \
    && git submodule update --init

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
    && if [ "x$COMMIT" != "x" ]; then \
        git clone --single-branch --branch $BRANCH $REPO_URL \
        && cd ./ngen \
        && git checkout $COMMIT; \
    else \
        git clone --depth 1 --branch $BRANCH $REPO_URL \
        && cd ./ngen ; \
    fi \
    && echo "#!/bin/bash" > build_sub \
    && echo "cmake -B \$1/cmake_build -DCMAKE_BUILD_TYPE=${NGEN_BUILD_CONFIG_TYPE} -S \$1" >> build_sub \
    && echo "cmake --build \$1/cmake_build" >> build_sub \
    #&& echo "cd \$1/cmake_build && make install" >> build_sub \
    && chmod u+x build_sub \
    && git submodule update --init --depth 1 test/googletest \
    && git submodule update --init --recursive --depth 1

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for building t-route in Rocky Linux environment
FROM rocky-ngen-deps as rocky_build_troute

ARG REPO_URL
ARG BRANCH
ARG COMMIT
ARG BUILD_PARALLEL_JOBS

COPY --chown=${USER} --from=rocky_init_troute_repo ${WORKDIR}/t-route ${WORKDIR}/t-route

USER root
RUN cp -s /usr/bin/python3 /usr/bin/python
USER ${USER}

#    && python(){ /usr/bin/python3 \$@; } && export -f python \
RUN cd ${WORKDIR}/t-route \
    && mkdir wheels \
    && pip3 install -r ./requirements.txt \
    && pip3 install wheel deprecated dask \
    && cd ${WORKDIR}/t-route \
    && cd ./src/python_routing_v02 \
    && ./compiler.sh \
    && python3 setup.py bdist_wheel \
    && cp dist/*.whl ${WORKDIR}/t-route/wheels/ \
    && cd ../python_framework_v02 \
    && python3 setup.py bdist_wheel \
    && cp dist/*.whl ${WORKDIR}/t-route/wheels/ \
    && cd ../nwm_routing \
    && python3 setup.py bdist_wheel \
    && cp dist/*.whl ${WORKDIR}/t-route/wheels/ \
    && cd ../ngen_routing \
    && python3 setup.py bdist_wheel \
    && cp dist/*.whl ${WORKDIR}/t-route/wheels/

USER root
RUN rm /usr/bin/python
USER ${USER}

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
ARG NGEN_NETCDF_ACTIVE
ARG NGEN_ROUTING_ACTIVE
ARG NGEN_UDUNITS_ACTIVE
ARG NGEN_UDUNITS_QUIET

ARG BUILD_NGEN_SERIAL
ARG BUILD_NGEN_PARALLEL
ARG BUILD_PARTITIONER
ARG BUILD_NOAH_OWP
ARG BUILD_CFE
ARG BUILD_TOPMODEL
ARG BUILD_PET
ARG BUILD_SLOTH

COPY --chown=${USER} --from=rocky_init_repo ${WORKDIR}/ngen ${WORKDIR}/ngen
COPY --chown=${USER} --from=rocky_build_troute ${WORKDIR}/t-route/wheels /tmp/t-route-wheels
COPY --chown=${USER} --from=rocky_build_troute ${WORKDIR}/t-route/requirements.txt /tmp/t-route-requirements.txt
ENV BOOST_ROOT=${WORKDIR}/boost

RUN cd ${WORKDIR}/ngen \
    && if [ "${NGEN_ACTIVATE_PYTHON}" == "ON" ]; then \
        pip3 install -r extern/test_bmi_py/requirements.txt; \
        if [ "${NGEN_ROUTING_ACTIVE}" == "ON" ] ; then \
            pip3 install /tmp/t-route-wheels/*.whl; pip3 install -r /tmp/t-route-requirements.txt; \
            fi; \
        fi \
    &&  if [ "${NGEN_ACTIVATE_FORTRAN}" == "ON" ]; then \
                ./build_sub extern/iso_c_fortran_bmi; \
                if [ "${BUILD_NOAH_OWP}" == "true" ] ; then ./build_sub extern/noah-owp-modular; fi; \
        fi \
    &&  if [ "${NGEN_ACTIVATE_C}" == "ON" ]; then \
                if [ "${BUILD_CFE}" == "true" ] ; then ./build_sub extern/cfe; fi; \
                if [ "${BUILD_PET}" == "true" ] ; then ./build_sub extern/evapotranspiration/evapotranspiration; fi; \
                if [ "${BUILD_TOPMODEL}" == "true" ] ; then ./build_sub extern/topmodel; fi; \
        fi \
    && if [ "${BUILD_SLOTH}" == "true" ] ; then ./build_sub extern/sloth; fi \
    && if [ "${BUILD_NGEN_SERIAL}" == "true" ]; then \
        cmake -B cmake_build_serial -S . \
        -DMPI_ACTIVE:BOOL=OFF \
        -DNETCDF_ACTIVE:BOOL=${NGEN_NETCDF_ACTIVE} \
        -DBMI_C_LIB_ACTIVE:BOOL=${NGEN_ACTIVATE_C} \
        -DBMI_FORTRAN_ACTIVE:BOOL=${NGEN_ACTIVATE_FORTRAN} \
        -DNGEN_ACTIVATE_PYTHON:BOOL=${NGEN_ACTIVATE_PYTHON} \
        -DNGEN_ACTIVATE_ROUTING:BOOL=${NGEN_ROUTING_ACTIVE} \
        -DUDUNITS_ACTIVE:BOOL=${NGEN_UDUNITS_ACTIVE} \
        -DUDUNITS_QUIET:BOOL=${NGEN_UDUNITS_QUIET} \
        -DCMAKE_INSTALL_PREFIX=${WORKDIR} \
        -DNETCDF_INCLUDE_DIR=/usr/include \
        -DNETCDF_LIBRARY=/usr/lib/libnetcdf.so \
        -DNETCDF_CXX_INCLUDE_DIR=/usr/local/include \
        -DNETCDF_CXX_LIBRARY=/usr/local/lib64/libnetcdf-cxx4.so ; \
    fi \
    && if [ "${BUILD_NGEN_PARALLEL}" == "true" ]; then \
        cmake -B cmake_build_parallel -S . \
        -DMPI_ACTIVE:BOOL=ON \
        -DNETCDF_ACTIVE:BOOL=${NGEN_NETCDF_ACTIVE} \
        -DBMI_C_LIB_ACTIVE:BOOL=${NGEN_ACTIVATE_C} \
        -DBMI_FORTRAN_ACTIVE:BOOL=${NGEN_ACTIVATE_FORTRAN} \
        -DNGEN_ACTIVATE_PYTHON:BOOL=${NGEN_ACTIVATE_PYTHON} \
        -DNGEN_ACTIVATE_ROUTING:BOOL=${NGEN_ROUTING_ACTIVE} \
        -DUDUNITS_ACTIVE:BOOL=${NGEN_UDUNITS_ACTIVE} \
        -DUDUNITS_QUIET:BOOL=${NGEN_UDUNITS_QUIET} \
        -DCMAKE_INSTALL_PREFIX=${WORKDIR} \
        -DNETCDF_INCLUDE_DIR=/usr/include \
        -DNETCDF_LIBRARY=/usr/lib/libnetcdf.so \
        -DNETCDF_CXX_INCLUDE_DIR=/usr/local/include \
        -DNETCDF_CXX_LIBRARY=/usr/local/lib64/libnetcdf-cxx4.so ; \
    fi \
    && ln -s $(if [ "${BUILD_NGEN_PARALLEL}" == "true" ]; then echo "cmake_build_parallel"; else echo "cmake_build_serial"; fi) cmake_build \
    &&  if [ "${BUILD_NGEN_PARTITIONER}" == "true" ]; then \
            cmake --build cmake_build --target partitionGenerator; \
            $BUILD_DIR/test/test_bmi_python; \
        fi \
    && for BUILD_DIR in $(if [ "${BUILD_NGEN_PARALLEL}" == "true" ]; then echo "cmake_build_parallel"; fi) $(if [ "${BUILD_NGEN_SERIAL}" == "true" ]; then echo "cmake_build_serial"; fi) ; do \
        cmake --build $BUILD_DIR --target ngen -j ${BUILD_PARALLEL_JOBS} \
        #Run the tests, if they fail, the image build fails \
        && cmake --build $BUILD_DIR --target test_unit -j ${BUILD_PARALLEL_JOBS} \
        && $BUILD_DIR/test/test_unit \
        # C++ functionality isn't separate, so always build the test_bmi_cpp shared lib (also needed for test_bmi_multi) \
        && ./build_sub extern/test_bmi_cpp \
        && cmake --build $BUILD_DIR --target test_bmi_cpp \
        && $BUILD_DIR/test/test_bmi_cpp \
        # For the external language BMI integrations, conditionally build the test packages/libraries and run tests \
        &&  if [ "${NGEN_ACTIVATE_C}" == "ON" ]; then \
                ./build_sub extern/test_bmi_c; \
                cmake --build $BUILD_DIR --target test_bmi_c; \
                $BUILD_DIR/test/test_bmi_c; \
            fi \
        &&  if [ "${NGEN_ACTIVATE_FORTRAN}" == "ON" ]; then \
                ./build_sub extern/test_bmi_fortran; \
                cmake --build $BUILD_DIR --target test_bmi_fortran; \
                $BUILD_DIR/test/test_bmi_fortran; \
            fi \
        &&  if [ "${NGEN_ACTIVATE_PYTHON}" == "ON" ]; then \
                cmake --build $BUILD_DIR --target test_bmi_python; \
                $BUILD_DIR/test/test_bmi_python; \
            fi \
        &&  if [ "${NGEN_ACTIVATE_C}" == "ON" ] && [ "${NGEN_ACTIVATE_FORTRAN}" == "ON" ] && [ "${NGEN_ACTIVATE_PYTHON}" == "ON" ]; then \
                cmake --build $BUILD_DIR --target test_bmi_multi; \
                $BUILD_DIR/test/test_bmi_multi; \
            fi \
    done \
    && find cmake_build* -type f -name "*" ! \( -name "*.so" -o -name "ngen" -o -name "partitionGenerator" \) -exec rm {} +

################################################################################################################
################################################################################################################
##### A build stage for testing using the ngen-build-test image
FROM rocky_build_ngen as rocky_ngen_build_testing

#COPY --chown=${USER} --from=rocky_init_repo ${WORKDIR}/ngen ${WORKDIR}/ngen
#ENV BOOST_ROOT=${WORKDIR}/boost
WORKDIR ${WORKDIR}/ngen

################################################################################################################
################################################################################################################
##### Model exec ngen worker image build stage
FROM rocky_build_ngen AS ngen_worker

ARG DATASET_DIRECTORIES

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
    && mkdir -p /dmod/shared_libs && chown ${USER} /dmod/shared_libs \
    && mkdir -p /dmod/bin && chown ${USER} /dmod/bin 
USER ${USER}

COPY --chown=${USER} entrypoint.sh ${WORKDIR}

ENV HYDRA_PROXY_RETRY_COUNT=5

# Change permissions for entrypoint and make sure dataset volume mount parent directories exists
RUN chmod +x ${WORKDIR}/entrypoint.sh \
    && for d in ${DATASET_DIRECTORIES}; do mkdir -p /dmod/datasets/${d}; done \
    && for d in noah-owp-modular topmodel cfe sloth 'evapotranspiration/evapotranspiration'; do \
        if [ -d ${WORKDIR}/ngen/extern/${d}/cmake_build ]; then \
            cp -a ${WORKDIR}/ngen/extern/${d}/cmake_build/*.so* /dmod/shared_libs/.; \
        fi; \
    done \
    && ( cp -a ${WORKDIR}/ngen/cmake_build_parallel/ngen /dmod/bin/ngen-parallel || true ) \
    && ( cp -a ${WORKDIR}/ngen/cmake_build_serial/ngen /dmod/bin/ngen-serial || true ) \
    && ( cp -a ${WORKDIR}/ngen/cmake_build/partitionGenerator /dmod/bin/partitionGenerator || true ) \
    && pushd /dmod/bin \
    && ( ( stat ngen-parallel && ln -s ngen-parallel ngen ) || ( stat ngen-serial && ln -s ngen-serial ngen ) ) \
    && popd 

WORKDIR ${WORKDIR}
ENV PATH=${WORKDIR}:$PATH
ENTRYPOINT ["entrypoint.sh"]
CMD [""]
