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
# Helper flag to, if "true" AND if COMMIT is not set, `git pull --ff-only` within the repo dir just before building ngen
ARG REFRESH_BEFORE_BUILD=true
ARG WORKDIR=/ngen

ARG TROUTE_REPO_URL=https://github.com/NOAA-OWP/t-route.git
ARG TROUTE_BRANCH=master
ARG TROUTE_COMMIT

ARG NGEN_CAL_BRANCH=master
ARG NGEN_CAL_COMMIT

ARG LGAR_C_REPO_URL="https://github.com/NOAA-OWP/LGAR-C.git"
ARG LGAR_C_BRANCH="master"
ARG LGAR_C_COMMIT

ARG SAC_SMA_REPO_URL="https://github.com/NOAA-OWP/sac-sma.git"
ARG SAC_SMA_BRANCH="master"
ARG SAC_SMA_COMMIT

ARG SNOW_17_REPO_URL="https://github.com/NOAA-OWP/snow17.git"
ARG SNOW_17_BRANCH="master"
ARG SNOW_17_COMMIT

#### Default arguments for required dependencies needed during various build stages
# The Rocky-Linux-based "base" stage, rocky-base
ARG ROCKY_BASE_REQUIRED="sudo openssh openssh-server bash git which"
# The Rocky-Linux-based "ngen-deps" stage, rocky-ngen-deps
# TODO: later look at separating build and run images again, and install static lib netcdf packages in run images
#ARG ROCKY_NGEN_DEPS_REQUIRED="mpich mpich-devel sudo gcc gcc-c++ make cmake tar git gcc-gfortran libgfortran \
#    python39 python39-devel python39-pip python39-numpy \
#    netcdf-cxx4-devel netcdf-cxx4-mpich-devel netcdf-fortran-devel netcdf-fortran-mpich-devel \
#    hdf5 hdf5-devel hdf5-mpich hdf5-mpich-devel \
#    bzip2 expat expat-devel flex bison udunits2 udunits2-devel"

ARG ROCKY_NGEN_DEPS_REQUIRED="sudo gcc gcc-c++ make cmake tar git gcc-gfortran libgfortran \
    python3 python3-devel python3-pip \
    bzip2 expat expat-devel flex bison udunits2 udunits2-devel zlib-devel sqlite-devel sqlite-libs gdal-devel"
# TODO: removed texinfo from list because it couldn't be found; make sure this doesn't lead to issues

ARG BOOST_VERSION=1.82.0
#mpich 3.2 doesn't work well gfortran 11 it seems, an alignment error crops up, but 3.3.2 seems to work...
ARG MPICH_VERSION="3.3.2"
ARG MIN_PYTHON="3.8.0"
ARG BLOSC2_VERSION

ARG NETCDF_C_VERSION=4.8.1
ARG NETCDF_CXX_VERSION=4.3.1
ARG NETCDF_FORTRAN_VERSION=4.6.0
ARG HD5_VERSION=1.10.9

# Work around Fortran MPI issue
ARG FCFLAGS="-w -fallow-argument-mismatch -O2"
ARG FFLAGS="-w -fallow-argument-mismatch -O2"
ARG MPICH_CONFIGURE_OPTIONS="--enable-shared"
ARG MPICH_MAKE_OPTIONS

ARG BUILD_PARALLEL_JOBS

ARG NGEN_WITH_BMI_C="ON"
ARG NGEN_WITH_BMI_FORTRAN="ON"
ARG NGEN_WITH_PYTHON="ON"
ARG NGEN_WITH_NETCDF="ON"
ARG NGEN_WITH_ROUTING="ON"
ARG NGEN_WITH_UDUNITS="ON"
ARG NGEN_UDUNITS_QUIET="ON"
ARG NGEN_WITH_SQLITE="ON"

ARG BUILD_NGEN_SERIAL="true"
ARG BUILD_NGEN_PARALLEL="true"
ARG BUILD_PARTITIONER="false"
ARG BUILD_NOAH_OWP="true"
ARG BUILD_CFE="true"
ARG BUILD_TOPMODEL="true"
ARG BUILD_PET="true"
ARG BUILD_SLOTH="true"

# BMI submodules (and fortran bindings) in ngen extern/ dir that should have shared libs copied to /dmod/shared_libs/
ARG NGEN_BMI_ACTIVE_SUBMODULES="iso_c_fortran_bmi SoilFreezeThaw SoilMoistureProfiles noah-owp-modular topmodel cfe sloth evapotranspiration"

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for Rocky-Linux-based "base"
FROM rockylinux:9.1 as rocky-base

ARG USER=mpi
ENV USER=${USER} USER_HOME=/home/${USER}
ENV SSHDIR=${USER_HOME}/.ssh

ARG ROCKY_BASE_REQUIRED

RUN dnf update -y \
    && dnf install -y 'dnf-command(config-manager)' \
    && dnf config-manager --set-enabled crb \
    && dnf install -y epel-release \
    && dnf -y install ${ROCKY_BASE_REQUIRED} \
    && dnf -y clean all \
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
    # Create DMOD-specific directory structure \
    && mkdir -p /dmod && chown ${USER} /dmod \
    && mkdir -p /dmod/datasets && chown ${USER} /dmod/datasets \
    #&& mkdir -p /dmod/shared_libs && chown ${USER} /dmod/shared_libs \
    && mkdir -p /dmod/lib && chown ${USER} /dmod/lib \
    && mkdir -p /dmod/lib64 && chown ${USER} /dmod/lib64 \
    && mkdir -p /dmod/include && chown ${USER} /dmod/include \
    && mkdir -p /dmod/bmi_module_data && chown ${USER} /dmod/bmi_module_data \
    && mkdir -p /dmod/bin && chown ${USER} /dmod/bin  \
    && mkdir -p /dmod/serial_bin && chown ${USER} /dmod/serial_bin  \
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
FROM rockylinux:9.1 AS download_boost

# Redeclaring inside this stage to get default from before first FROM
ARG BOOST_VERSION

# Copy this file here is just to avoid failure if there is no boost_*.tar.* present.
# Use essentially a dummy file that won't change (unless someone does that deliberately to trigger a full rebuild), as
#   any change to this file will cause anything and and build layer/stage that uses boost to be fully rebuilt.
COPY .boost_local_copying.md boost_*.tar.* ${WORKDIR}

RUN mkdir /boost \
    && if compgen -G "${WORKDIR}/boost_${BOOST_VERSION//./_}.tar.*" > /dev/null; then \
        mv ${WORKDIR}/boost_${BOOST_VERSION//./_}.tar.* /boost/boost_tarball.blob ; \
    else \
        curl -L -o /boost/boost_tarball.blob https://sourceforge.net/projects/boost/files/boost/${BOOST_VERSION}/boost_${BOOST_VERSION//./_}.tar.bz2/download ; \
    fi

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for downloading MPICH
FROM rockylinux:9.1 AS download_mpich

# Redeclaring inside this stage to get default from before first FROM
ARG MPICH_VERSION

RUN curl -o /tmp/mpich-${MPICH_VERSION}.tar.gz https://www.mpich.org/static/downloads/${MPICH_VERSION}/mpich-${MPICH_VERSION}.tar.gz


################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for downloading MPICH
FROM rockylinux:9.1 AS download_hd5

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

# Set up pip constraints file for this and descendent stages
COPY constraints.txt ${WORKDIR}/constraints.txt
ENV PIP_CONSTRAINT=${WORKDIR}/constraints.txt

# TODO: later, go back and change all pip3/python3 to just pip/python (but leave for now to limit scope)
# Note that this includes numpy, which is needed for Python BMI support, regardless of BMI module
USER root
RUN dnf update -y && dnf install -y ${ROCKY_NGEN_DEPS_REQUIRED} && dnf clean -y all \
    && ln -s $(which python3) $(which python3 | sed 's/python3/python/') \
    && pip install --no-cache-dir pip wheel packaging \
    && if [ "${NGEN_WITH_PYTHON}" == "ON" ]; then pip install --no-cache-dir numpy; fi
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
##### Create intermediate Docker build stage for Rocky-Linux-based "ngen-deps"
FROM rocky-ngen-packaged-deps as rocky-ngen-deps

ARG BOOST_VERSION
ARG WORKDIR

ENV WORKDIR=${WORKDIR}
ENV BOOST_ROOT=${WORKDIR}/boost

COPY --chown=${USER} --from=download_boost /boost ${WORKDIR}/boost

ARG MPICH_VERSION
ARG MIN_PYTHON
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

ARG NGEN_WITH_ROUTING

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
    # mpich3 and gfortran > 10 don't get along...https://gcc.gnu.org/bugzilla/show_bug.cgi?id=91731 \
    && FFLAGS="-w -fallow-argument-mismatch -O2"  ./configure ${MPICH_CONFIGURE_OPTIONS} \
    && make -j ${BUILD_PARALLEL_JOBS} ${MPICH_MAKE_OPTIONS} && make install \
    ##### Build and install HDF5 \
    && cd /tmp/ngen-deps \
    && tar -xzf hdf5-${HD5_VERSION}.tar.gz \
    && cd hdf5-${HD5_VERSION} \
    && ./configure --enable-parallel --prefix=/usr \
    && make -j ${BUILD_PARALLEL_JOBS} && make install \
    ##### Build and install NetCDF C \
    && cd /tmp/ngen-deps \
    && mkdir netcdf \
    && tar -xzf netcdf-${NETCDF_C_VERSION}.tar.gz -C netcdf --strip 1 \
    && cd netcdf \
    # Make sure the netcdf prefix and install dirs align with t-route env var NETCDFINC set a little further below \
    && LIBS=curl && ./configure --enable-shared --prefix=/usr \
    && make -j ${BUILD_PARALLEL_JOBS} && make install \
    # TODO: if we run into any problem, might need to reactivate this \
    #&& make check \
    ##### Build and install NetCDF Fortran \
    && cd /tmp/ngen-deps \
    && mkdir netcdf-fortran \
    && tar -xzf netcdf-fortran-${NETCDF_FORTRAN_VERSION}.tar.gz -C netcdf-fortran --strip 1 \
    && cd netcdf-fortran \
    && export NCDIR=/usr NFDIR=/usr \
    && LD_LIBRARY_PATH=/usr/lib CPPFLAGS=-I/usr/include LDFLAGS=-L/usr/lib ./configure --prefix=/usr \
    && make -j ${BUILD_PARALLEL_JOBS} && make install \
    ##### Build and install NetCDF C++ \
    && cd /tmp/ngen-deps \
    && mkdir netcdf-cxx4 \
    && tar -xzf netcdf-cxx4-${NETCDF_CXX_VERSION}.tar.gz -C netcdf-cxx4 --strip 1 \
    && mkdir netcdf-cxx4/build \
    && cd netcdf-cxx4/build \
    && cmake .. \
    && make -j ${BUILD_PARALLEL_JOBS} \
    # TODO: if we run into any problem, might need to reactivate this \
    # && ctest \
    && make install \
    # Set the regular user as the owner of the BOOST_ROOT dir we copied in \
    && chown -R ${USER}:${USER} ${BOOST_ROOT} \
    && rm -rf /tmp/ngen-deps

ENV PATH=${PATH}:/usr/lib64/mpich/bin
ENV LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/lib:/usr/local/lib64
# This next value is eventually needed for the t-route build ...
# ... make sure it stays in sync with configure step for netcdf above
ENV NETCDFINC=/usr/include
ENV CC=gcc

# Get this for the times we need to install t-route
COPY --from=rocky_init_troute_repo ${WORKDIR}/t-route/requirements.txt ${WORKDIR}/t-route-requirements.txt

# Install troute and required Python packages, with some deps needing some special attention
RUN if [ "${NGEN_WITH_ROUTING}" == "ON" ]; then \
      # Get subset of requirements needed first (including version specifiers if present) because of netCDF4 handling \
      cat ${WORKDIR}/t-route-requirements.txt | grep -i numpy >> first_reqs.txt ; \
      cat ${WORKDIR}/t-route-requirements.txt | grep -i pandas | grep -v geo >> first_reqs.txt ; \
      cat ${WORKDIR}/t-route-requirements.txt | grep -i pyyaml >> first_reqs.txt ; \
      cat ${WORKDIR}/t-route-requirements.txt | grep -i cython >> first_reqs.txt ; \
      cat ${WORKDIR}/t-route-requirements.txt | grep -i pyarrow >> first_reqs.txt ; \
      pip3 install --no-cache-dir -r first_reqs.txt ; \
      rm first_reqs.txt ; \
      # Then install a few more things, including a particular blosc2 version and an adjusted build of tables \
      pip3 install --no-cache-dir bmipy blosc2==${BLOSC2_VERSION:-2.0.0} build wheel packaging pyproj fiona geopandas ; \
      env HDF5_DIR=/usr pip3 install --no-cache-dir --no-build-isolation tables ; \
      env HDF5_DIR=/usr pip3 install --no-cache-dir netCDF4==1.6.3 ; \
      # Then install remaining t-route requirements
      pip3 install --no-cache-dir -r ${WORKDIR}/t-route-requirements.txt ; \
    fi \
    && rm ${WORKDIR}/t-route-requirements.txt

USER ${USER}

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for building framework in Rocky Linux environment
FROM rocky-base as rocky_init_repo
ARG REPO_URL
ARG NGEN_BUILD_CONFIG_TYPE
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
###### Create intermediate Docker build stage for building t-route in Rocky Linux environment
FROM rocky-ngen-deps as rocky_build_troute

ARG TROUTE_REPO_URL
ARG TROUTE_BRANCH
ARG TROUTE_COMMIT
ARG BUILD_PARALLEL_JOBS
ARG NGEN_WITH_ROUTING

COPY --chown=${USER} --from=rocky_init_troute_repo ${WORKDIR}/t-route ${WORKDIR}/t-route

#    && python(){ /usr/bin/python3 \$@; } && export -f python \
RUN if [ "${NGEN_WITH_ROUTING}" == "ON" ]; then \
      export FC=gfortran ; \
      export F90=gfortran ; \
      mkdir ${WORKDIR}/t-route/wheels \
      && cd ${WORKDIR}/t-route \
      && ./compiler.sh \
      && cd ${WORKDIR}/t-route/src/troute-network \
      && python3 setup.py --use-cython bdist_wheel \
      && cp dist/*.whl ${WORKDIR}/t-route/wheels/ \
      && cd ${WORKDIR}/t-route/src/troute-routing \
      && python3 setup.py --use-cython bdist_wheel \
      && cp dist/*.whl ${WORKDIR}/t-route/wheels/ \
      && cd ${WORKDIR}/t-route/src/troute-config \
      # troute-config doesn't use setup.py ... use build to make the wheel \
      #&& python3 setup.py --use-cython bdist_wheel \
      && python3 -m build . \
      && cp dist/*.whl ${WORKDIR}/t-route/wheels/ \
      && cd ${WORKDIR}/t-route/src/troute-nwm \
      # troute-nwm doesn't use setup.py ... use build to make the wheel; see https://github.com/NOAA-OWP/t-route/pull/784 \
      && python3 -m build . \
      && cp dist/*.whl ${WORKDIR}/t-route/wheels/ ; \
    fi

USER root
RUN rm /usr/bin/python
USER ${USER}

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for building ISO_C_BINDINGS for Fortran BMI modules
FROM rocky-ngen-deps as pre_build_bmi_iso_c_fortran_dep

ARG NGEN_BUILD_CONFIG_TYPE

COPY --chown=${USER} --from=rocky_init_repo ${WORKDIR}/ngen/extern/iso_c_fortran_bmi ${WORKDIR}/iso_c_fortran_bmi
WORKDIR ${WORKDIR}
RUN cmake -B ./iso_c_fortran_bmi/cmake_build -DCMAKE_BUILD_TYPE=${NGEN_BUILD_CONFIG_TYPE:?} -S ./iso_c_fortran_bmi \
    && cmake --build ./iso_c_fortran_bmi/cmake_build

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for building LGAR_C
FROM rocky-ngen-deps as build_bmi_lgar_c

ARG NGEN_BUILD_CONFIG_TYPE
ARG LGAR_C_REPO_URL
ARG LGAR_C_BRANCH
ARG LGAR_C_COMMIT

RUN git clone \
        --single-branch \
        --branch ${LGAR_C_BRANCH:?No lgar-c branch set} \
        ${LGAR_C_REPO_URL:?No lgar-c repo set} \
        ${WORKDIR}/lgar-c \
    && cd ${WORKDIR}/lgar-c \
    && if [ "x$LGAR_C_COMMIT" != "x" ]; then git checkout $LGAR_C_COMMIT ; fi \
    && cmake -B ./cmake_build \
            -DCMAKE_BUILD_TYPE=${NGEN_BUILD_CONFIG_TYPE:?} \
            -DNGEN=ON  \
            -DCMAKE_INSTALL_PREFIX:PATH=/dmod \
            -S . \
    && cmake --build ./cmake_build \
    && cmake --build ./cmake_build --target install \
    && mkdir -p /dmod/shared_libs \
    && cp -a /dmod/lib64/liblasambmi.so* /dmod/shared_libs/ \
    # An extra bit here for copying lgar-c data \
    && mkdir -p /dmod/bmi_module_data/lgar-c/data \
    && cp -a ./data/ /dmod/bmi_module_data/lgar-c/data/ \
    # Clean-up a little more for Release builds \
    && if [ "${NGEN_BUILD_CONFIG_TYPE}" == "Release" ]; then cd ${WORKDIR} && rm -rf ${WORKDIR}/lgar-c ; fi

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for building Sac-SMA
FROM rocky-ngen-deps as build_bmi_sac_sma

ARG NGEN_BUILD_CONFIG_TYPE
ARG SAC_SMA_REPO_URL
ARG SAC_SMA_BRANCH
ARG SAC_SMA_COMMIT

COPY --chown=${USER} --from=pre_build_bmi_iso_c_fortran_dep ${WORKDIR}/iso_c_fortran_bmi ${WORKDIR}/iso_c_fortran_bmi

# Note the second layer in the directory structure (i.e., sac-sma/sac-sma is the actual repo dir)
# Doing this to align with repo instructions
RUN mkdir ${WORKDIR}/sac-sma \
    && git clone \
        --single-branch \
        --branch ${SAC_SMA_BRANCH:?No sac-sma branch set} \
        ${SAC_SMA_REPO_URL:?No sac-sma repo set} \
        ${WORKDIR}/sac-sma/sac-sma \
    && cd ${WORKDIR}/sac-sma \
    && if [ "x$SAC_SMA_COMMIT" != "x" ]; then cd ./sac-sma && git checkout $SAC_SMA_COMMIT && cd .. ; fi \
    && cp ./sac-sma/ngen_files/sacbmi.pc.in ./sac-sma/ngen_files/CMakeLists.txt . \
    && cmake -B ./cmake_build -DCMAKE_BUILD_TYPE=${NGEN_BUILD_CONFIG_TYPE:?} -DCMAKE_INSTALL_PREFIX:PATH=/dmod -S . \
    && cmake --build ./cmake_build --target all \
    && mkdir -p /dmod/shared_libs \
    && cp -a ./cmake_build/*.so* /dmod/lib64/. \
    && cp -a ./cmake_build/*.so* /dmod/shared_libs/. \
    # Clean-up a little more for Release builds \
    && if [ "${NGEN_BUILD_CONFIG_TYPE}" == "Release" ]; then cd ${WORKDIR} && rm -rf ${WORKDIR}/sac-sma ; fi

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for building SNOW_17
FROM rocky-ngen-deps as build_bmi_snow_17

ARG NGEN_BUILD_CONFIG_TYPE
ARG SNOW_17_REPO_URL
ARG SNOW_17_BRANCH
ARG SNOW_17_COMMIT

# Snow17 needs iso_c_fortran_bmi built, and it needs it at ../iso_c_fortran_bmi (i.e., as if snow17 was under extern)

COPY --chown=${USER} --from=pre_build_bmi_iso_c_fortran_dep ${WORKDIR}/iso_c_fortran_bmi ${WORKDIR}/iso_c_fortran_bmi

RUN git clone \
        --single-branch \
        --branch ${SNOW_17_BRANCH:?No snow-17 branch set} \
        ${SNOW_17_REPO_URL:?No snow-17 repo set} \
        ${WORKDIR}/snow-17 \
    && cd ${WORKDIR}/snow-17 \
    && if [ "x$SNOW_17_COMMIT" != "x" ]; then git checkout $SNOW_17_COMMIT ; fi \
    && cmake -B ./cmake_build -DCMAKE_BUILD_TYPE=${NGEN_BUILD_CONFIG_TYPE:?} -DCMAKE_INSTALL_PREFIX:PATH=/dmod -S . \
    && cmake --build ./cmake_build \
    && mkdir -p /dmod/shared_libs \
    && cp -a ./cmake_build/*.so* /dmod/lib64/. \
    && cp -a ./cmake_build/*.so* /dmod/shared_libs/. \
    # Clean-up a little more for Release builds \
    && if [ "${NGEN_BUILD_CONFIG_TYPE}" == "Release" ]; then cd ${WORKDIR} && rm -rf ${WORKDIR}/snow-17 ; fi

################################################################################################################
################################################################################################################
##### Create intermediate Docker build stage for building framework in Rocky Linux environment
FROM rocky-ngen-deps as rocky_build_ngen

ARG REPO_URL
ARG BRANCH
ARG COMMIT
ARG REFRESH_BEFORE_BUILD
ARG BUILD_PARALLEL_JOBS

ARG NGEN_BUILD_CONFIG_TYPE
ARG NGEN_WITH_BMI_C
ARG NGEN_WITH_BMI_FORTRAN
ARG NGEN_WITH_PYTHON
ARG NGEN_WITH_NETCDF
ARG NGEN_WITH_ROUTING
ARG NGEN_WITH_UDUNITS
ARG NGEN_UDUNITS_QUIET
ARG NGEN_WITH_SQLITE

ARG NGEN_BMI_ACTIVE_SUBMODULES

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
COPY --chown=${USER} --from=rocky_build_troute ${WORKDIR}/t-route/src/kernel /tmp/t-route-kernels
COPY --chown=${USER} --from=rocky_build_troute ${WORKDIR}/t-route/requirements.txt /tmp/t-route-requirements.txt
ENV BOOST_ROOT=${WORKDIR}/boost

USER root
RUN if [ "${NGEN_WITH_PYTHON}" == "ON" ]; then \
        chgrp -R ${USER} /usr/local/lib*/python3.* ; \
        chmod -R g+sw /usr/local/lib*/python3.* ; \
    fi
USER ${USER}

ENV VIRTUAL_ENV=/dmod/venv
RUN python3 -m venv $VIRTUAL_ENV && pip3 install numpy
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN cd ${BOOST_ROOT} \
    && tar -xf boost_tarball.blob --strip 1 \
    && rm boost_tarball.blob \
    && cd ${WORKDIR}/ngen \
    &&  if [ -z "${COMMIT:-}" ]; then \
            if [ "${REFRESH_BEFORE_BUILD:-}" = "true" ] ; then  \
                git pull --ff-only ; \
                git submodule update --init --depth 1 test/googletest ; \
                git submodule update --init --recursive --depth 1 ; \
            fi ; \
        fi \
    # C++ functionality isn't separate, so always build the test_bmi_cpp shared lib \
    && ./build_sub extern/test_bmi_cpp \
    &&  if [ "${NGEN_WITH_PYTHON}" == "ON" ]; then \
            pip3 install --no-cache-dir -r extern/test_bmi_py/requirements.txt; \
            if [ "${NGEN_WITH_ROUTING}" == "ON" ] ; then \
                pip3 install --no-cache-dir /tmp/t-route-wheels/*.whl ; \
            fi; \
        fi \
    && if [ "${BUILD_NGEN_SERIAL}" == "true" ]; then \
        cmake -B cmake_build_serial -S . \
            -DCMAKE_BUILD_TYPE=${NGEN_BUILD_CONFIG_TYPE} \
            -DNGEN_WITH_MPI:BOOL=OFF \
            -DNGEN_WITH_NETCDF:BOOL=${NGEN_WITH_NETCDF} \
            -DNGEN_WITH_BMI_C:BOOL=${NGEN_WITH_BMI_C} \
            -DNGEN_WITH_BMI_FORTRAN:BOOL=${NGEN_WITH_BMI_FORTRAN} \
            -DNGEN_WITH_PYTHON:BOOL=${NGEN_WITH_PYTHON} \
            -DNGEN_WITH_ROUTING:BOOL=${NGEN_WITH_ROUTING} \
            -DNGEN_WITH_UDUNITS:BOOL=${NGEN_WITH_UDUNITS} \
            -DUDUNITS_QUIET:BOOL=${NGEN_UDUNITS_QUIET} \
            -DNGEN_WITH_SQLITE=${NGEN_WITH_SQLITE} \
            -DCMAKE_INSTALL_PREFIX=/dmod \
            -DNETCDF_INCLUDE_DIR=/usr/include \
            -DNETCDF_LIBRARY=/usr/lib/libnetcdf.so \
            -DNETCDF_CXX_INCLUDE_DIR=/usr/local/include \
            -DNETCDF_CXX_LIBRARY=/usr/local/lib64/libnetcdf-cxx4.so ; \
    fi \
    && if [ "${BUILD_NGEN_PARALLEL}" == "true" ]; then \
        cmake -B cmake_build_parallel -S . \
            -DCMAKE_BUILD_TYPE=${NGEN_BUILD_CONFIG_TYPE} \
            -DNGEN_WITH_MPI:BOOL=ON \
            -DNGEN_WITH_NETCDF:BOOL=${NGEN_WITH_NETCDF} \
            -DNGEN_WITH_BMI_C:BOOL=${NGEN_WITH_BMI_C} \
            -DNGEN_WITH_BMI_FORTRAN:BOOL=${NGEN_WITH_BMI_FORTRAN} \
            -DNGEN_WITH_PYTHON:BOOL=${NGEN_WITH_PYTHON} \
            -DNGEN_WITH_ROUTING:BOOL=${NGEN_WITH_ROUTING} \
            -DNGEN_WITH_UDUNITS:BOOL=${NGEN_WITH_UDUNITS} \
            -DUDUNITS_QUIET:BOOL=${NGEN_UDUNITS_QUIET} \
            -DNGEN_WITH_SQLITE=${NGEN_WITH_SQLITE} \
            -DCMAKE_INSTALL_PREFIX=/dmod \
            -DNETCDF_INCLUDE_DIR=/usr/include \
            -DNETCDF_LIBRARY=/usr/lib/libnetcdf.so \
            -DNETCDF_CXX_INCLUDE_DIR=/usr/local/include \
            -DNETCDF_CXX_LIBRARY=/usr/local/lib64/libnetcdf-cxx4.so ; \
    fi \
    && ln -s $(if [ "${BUILD_NGEN_PARALLEL}" == "true" ]; then echo "cmake_build_parallel"; else echo "cmake_build_serial"; fi) cmake_build \
    &&  if [ "${BUILD_NGEN_PARTITIONER}" == "true" ]; then \
            cmake --build cmake_build --target partitionGenerator -- -j ${BUILD_PARALLEL_JOBS}; \
            $BUILD_DIR/test/test_bmi_python; \
        fi \
    && for BUILD_DIR in $(if [ "${BUILD_NGEN_PARALLEL}" == "true" ]; then echo "cmake_build_parallel"; fi) $(if [ "${BUILD_NGEN_SERIAL}" == "true" ]; then echo "cmake_build_serial"; fi) ; do \
        cmake --build $BUILD_DIR --target ngen -- -j ${BUILD_PARALLEL_JOBS} \
        #Run the tests, if they fail, the image build fails \
        && cmake --build $BUILD_DIR --target test_unit -- -j ${BUILD_PARALLEL_JOBS} \
        && $BUILD_DIR/test/test_unit \
        # C++ functionality isn't separate, so always build and run the test_bmi_cpp testing target \
        && cmake --build $BUILD_DIR --target test_bmi_cpp -- -j ${BUILD_PARALLEL_JOBS} \
        && $BUILD_DIR/test/test_bmi_cpp \
        # For the external language BMI integrations, conditionally build the test packages/libraries and run tests \
        &&  if [ "${NGEN_WITH_BMI_C}" == "ON" ]; then \
                cmake --build $BUILD_DIR --target test_bmi_c -- -j ${BUILD_PARALLEL_JOBS}; \
                $BUILD_DIR/test/test_bmi_c; \
            fi \
        &&  if [ "${NGEN_WITH_BMI_FORTRAN}" == "ON" ]; then \
                cmake --build $BUILD_DIR --target test_bmi_fortran -- -j ${BUILD_PARALLEL_JOBS}; \
                $BUILD_DIR/test/test_bmi_fortran; \
            fi \
        &&  if [ "${NGEN_WITH_PYTHON}" == "ON" ]; then \
                cmake --build $BUILD_DIR --target test_bmi_python -- -j ${BUILD_PARALLEL_JOBS} ; \
                $BUILD_DIR/test/test_bmi_python; \
            fi \
        &&  if [ "${NGEN_WITH_BMI_C}" == "ON" ] && [ "${NGEN_WITH_BMI_FORTRAN}" == "ON" ] && [ "${NGEN_WITH_PYTHON}" == "ON" ]; then \
                cmake --build $BUILD_DIR --target test_bmi_multi -- -j ${BUILD_PARALLEL_JOBS}; \
                $BUILD_DIR/test/test_bmi_multi; \
            fi ; \
    done \
    && rm -rf ${BOOST_ROOT} \
    && mkdir -p /dmod/bin \
    && chown ${USER} /dmod/bin \
    && mkdir -p /dmod/shared_libs \
    && chown ${USER} /dmod/shared_libs \
    && mkdir -p /dmod/datasets \
    && chown ${USER} /dmod/datasets \
    && if [ "${BUILD_NGEN_PARALLEL}" == "true" ]; then cp -a ${WORKDIR}/ngen/cmake_build_parallel/ngen /dmod/bin/ngen-parallel ; fi \
    && if [ "${BUILD_NGEN_SERIAL}" == "true" ]; then cp -a ${WORKDIR}/ngen/cmake_build_serial/ngen /dmod/bin/ngen-serial ; fi \
    && for d in ${NGEN_BMI_ACTIVE_SUBMODULES:?List of active BMI git submodules not defined}; do \
            if [ -d ${WORKDIR}/ngen/extern/${d}/cmake_build ]; then \
                cp -a ${WORKDIR}/ngen/extern/${d}/cmake_build/*.so* /dmod/shared_libs/.; \
            elif [ -d ${WORKDIR}/ngen/extern/${d}/${d}/cmake_build ]; then \
                cp -a ${WORKDIR}/ngen/extern/${d}/${d}/cmake_build/*.so* /dmod/shared_libs/.; \
            fi; \
        done \
    && cd ${WORKDIR} \
    && if [ "${NGEN_BUILD_CONFIG_TYPE:?}" != "Debug" ]; then rm -rf ${WORKDIR}/ngen ; fi

ENV PATH=${WORKDIR}:${WORKDIR}/bin:/dmod/bin:$PATH

################################################################################################################
################################################################################################################
##### A build stage for testing using the ngen-build-test image
FROM rocky-ngen-deps as rocky_ngen_build_testing
#FROM rocky_build_ngen as rocky_ngen_build_testing
#FROM ${DOCKER_INTERNAL_REGISTRY}/ngen-deps:latest as rocky_ngen_build_testing

COPY --chown=${USER} --from=rocky_init_repo ${WORKDIR}/ngen ${WORKDIR}/ngen

ENV BOOST_ROOT=${WORKDIR}/boost

USER root
RUN if [ "${NGEN_WITH_PYTHON}" == "ON" ]; then \
        chgrp -R ${USER} /usr/local/lib*/python3.* ; \
        chmod -R g+sw /usr/local/lib*/python3.* ; \
    fi
USER ${USER}

ENV VIRTUAL_ENV=/dmod/venv
RUN if [ "${NGEN_WITH_PYTHON}" == "ON" ]; then python3 -m venv ${VIRTUAL_ENV} ; fi
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN if [ "${NGEN_WITH_PYTHON}" == "ON" ]; then pip install numpy ; fi

RUN cd ${BOOST_ROOT} && tar -xf boost_tarball.blob --strip 1 && rm boost_tarball.blob
ENV BOOST_ROOT=${WORKDIR}/boost
#COPY --chown=${USER} --from=rocky_build_troute ${WORKDIR}/t-route/wheels /tmp/t-route-wheels
#COPY --chown=${USER} --from=rocky_build_troute ${WORKDIR}/t-route/requirements.txt /tmp/t-route-requirements.txt
WORKDIR ${WORKDIR}/ngen

################################################################################################################
################################################################################################################
##### A build stage for the partitioner utility image
FROM rocky-ngen-deps as partitioner_image

ARG BUILD_PARALLEL_JOBS
ARG COMMIT
ARG REFRESH_BEFORE_BUILD
ARG NGEN_WITH_BMI_C
ARG NGEN_WITH_BMI_FORTRAN
ARG NGEN_WITH_PYTHON
ARG NGEN_WITH_NETCDF
ARG NGEN_WITH_UDUNITS
ARG NGEN_UDUNITS_QUIET
ARG NGEN_WITH_SQLITE
ARG NGEN_BUILD_CONFIG_TYPE
ARG PARTITIONER_EXECUTABLE

COPY --chown=${USER} partitioner_entrypoint.sh ${WORKDIR}/entrypoint.sh
COPY --chown=${USER} --from=rocky_init_repo ${WORKDIR}/ngen ${WORKDIR}/ngen
ENV BOOST_ROOT=${WORKDIR}/boost

RUN cd ${BOOST_ROOT} \
    && tar -xf boost_tarball.blob --strip 1 \
    && rm boost_tarball.blob \
    && cd ${WORKDIR}/ngen \
    &&  if [ "x$COMMIT" = "x" ]; then \
            if [ "${REFRESH_BEFORE_BUILD:-}" = "true" ] ; then  \
                git pull --ff-only ; \
            fi ; \
        fi \
    && if [ -z "${PARTITIONER_EXECUTABLE:-}" ]; then echo "Error: target/executable name not set" 2>&1 ; exit 1; fi \
    && cmake -B cmake_build -S . \
               -DCMAKE_BUILD_TYPE=${NGEN_BUILD_CONFIG_TYPE} \
               -DNGEN_WITH_MPI:BOOL=OFF \
               -DNGEN_WITH_NETCDF:BOOL=${NGEN_WITH_NETCDF} \
               #-DNGEN_WITH_BMI_C:BOOL=${NGEN_WITH_BMI_C} \
               #-DNGEN_WITH_BMI_FORTRAN:BOOL=${NGEN_WITH_BMI_FORTRAN} \
               #-DNGEN_WITH_PYTHON:BOOL=${NGEN_WITH_PYTHON} \
               #-DNGEN_WITH_ROUTING:BOOL=${NGEN_WITH_ROUTING} \
               -DNGEN_WITH_UDUNITS:BOOL=${NGEN_WITH_UDUNITS} \
               -DUDUNITS_QUIET:BOOL=${NGEN_UDUNITS_QUIET} \
               -DNGEN_WITH_SQLITE=${NGEN_WITH_SQLITE} \
               -DCMAKE_INSTALL_PREFIX=${WORKDIR} \
               -DNETCDF_INCLUDE_DIR=/usr/include \
               -DNETCDF_LIBRARY=/usr/lib/libnetcdf.so \
               -DNETCDF_CXX_INCLUDE_DIR=/usr/local/include \
               -DNETCDF_CXX_LIBRARY=/usr/local/lib64/libnetcdf-cxx4.so \
    && cmake --build cmake_build --target ${PARTITIONER_EXECUTABLE} -- -j ${BUILD_PARALLEL_JOBS} \
    #FIXME remove the data copy, only there for temporary testing \
    && mkdir ${WORKDIR}/bin  \
    && cp cmake_build/${PARTITIONER_EXECUTABLE} ${WORKDIR}/bin \
    && cd ${WORKDIR}  \
    && rm -rf ngen \
    && ls -lah ${BOOST_ROOT} \
    && rm -rf ${BOOST_ROOT} 2>/dev/null \
    && chmod +x ${WORKDIR}/entrypoint.sh

WORKDIR ${WORKDIR}
ENV LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/lib:/usr/local/lib64:/dmod/shared_libs
# This next value is eventually needed for the t-route build ...
# ... make sure it stays in sync with configure step for netcdf above
ENV NETCDFINC=/usr/include
ENV PATH=/dmod/bin:${WORKDIR}:${WORKDIR}/bin:$PATH:/usr/lib64/mpich/bin
ENV NGEN_PART_EXECUTABLE="${PARTITIONER_EXECUTABLE}"
ENTRYPOINT ["entrypoint.sh"]

################################################################################################################
################################################################################################################
##### User customization build stage
FROM rocky-ngen-deps as build_customizations

ARG WORKDIR
ARG NGEN_BUILD_CONFIG_TYPE
ENV NGEN_BUILD_CONFIG_TYPE=${NGEN_BUILD_CONFIG_TYPE}

COPY --chown=${USER} --from=pre_build_bmi_iso_c_fortran_dep ${WORKDIR}/iso_c_fortran_bmi ${WORKDIR}/iso_c_fortran_bmi

ENV PATH=${WORKDIR}:${WORKDIR}/bin:/dmod/bin:${PATH}:/usr/lib64/mpich/bin
ENV LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/lib:/usr/local/lib64:/dmod/shared_libs
ENV NETCDFINC=/usr/include
ENV VIRTUAL_ENV=/dmod/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy customization script and any other included artifacts (plus README, to make sure something is always there)
COPY customize/* ${WORKDIR}

# Install packages from a requirements.txt if present
RUN if [ -e ${WORKDIR}/requirements.txt ]; then pip3 install -r ${WORKDIR}/requirements.txt ; fi

# Clone, build, and install simple CMake-buildable repos if the list is present
RUN if [ -e ${WORKDIR}/cmake_repositories.txt ]; then \
        chmod ugo+x ${WORKDIR}/clone_and_cmake_build.sh ; \
        for _REPO_URL in $(cat ${WORKDIR}/cmake_repositories.txt); do \
            ${WORKDIR}/clone_and_cmake_build.sh ${_REPO_URL} ; \
        done ; \
    fi

# If the user script exists and was copied, execute it
RUN if [ -e ${WORKDIR}/customize.sh ]; then chmod ugo+x ${WORKDIR}/customize.sh && ${WORKDIR}/customize.sh ; fi

################################################################################################################
################################################################################################################
##### Model exec ngen worker image build stage
#FROM rocky_build_ngen AS ngen_worker
FROM rocky-base AS ngen_worker

COPY --from=rocky_build_ngen / /

ARG NGEN_BMI_ACTIVE_SUBMODULES
ARG DATASET_DIRECTORIES
ARG WORKDIR

ENV WORKDIR=${WORKDIR}
ENV HYDRA_HOST_FILE=/etc/opt/hosts
ENV PATH=${WORKDIR}:${WORKDIR}/bin:/dmod/bin:${PATH}:/usr/lib64/mpich/bin

ENV LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/lib:/usr/local/lib64:/dmod/shared_libs
# This next value is eventually needed for the t-route build ...
# ... make sure it stays in sync with configure step for netcdf above
ENV NETCDFINC=/usr/include
ENV VIRTUAL_ENV=/dmod/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

#RUN cd ./ngen && mkdir ${WORKDIR}/bin && cp cmake_build/ngen ${WORKDIR}/bin && cp -r data ${WORKDIR}/data \
#    && cd $WORKDIR && rm -rf ngen boost

# Copy libs/data/etc. from various per-module stages
COPY --chown=${USER} --from=build_bmi_lgar_c /dmod/ /dmod/
COPY --chown=${USER} --from=build_bmi_sac_sma /dmod/ /dmod/
COPY --chown=${USER} --from=build_bmi_snow_17 /dmod/ /dmod/

#  Copy libs data, etc. from customize layer
COPY --chown=${USER} --from=build_customizations /dmod/ /dmod/

USER root
# Update path and make sure dataset directory is there
RUN echo "export PATH=${PATH}" >> /etc/profile \
    && sed -i "s/PasswordAuthentication yes/#PasswordAuthentication yes/g" /etc/ssh/sshd_config \
    && sed -i "s/PermitRootLogin yes/PermitRootLogin no/g" /etc/ssh/sshd_config \
    && sed -i "s/#ClientAliveInterval.*/ClientAliveInterval 60/" /etc/ssh/sshd_config \
    && sed -i "s/#ClientAliveCountMax.*/ClientAliveCountMax 5/" /etc/ssh/sshd_config \
    && if [ -f /var/run/nologin ]; then rm /var/run/nologin ; fi ;
USER ${USER}

COPY --chown=${USER} noah_owp_parameters /dmod/bmi_module_data/noah_owp/parameters/
COPY --chown=${USER} ngen_entrypoint.sh ${WORKDIR}/entrypoint.sh
COPY --chown=${USER} funcs.sh ${WORKDIR}
COPY --chown=${USER} --chmod=744 py_funcs.py /dmod/bin/py_funcs

ENV HYDRA_PROXY_RETRY_COUNT=5

# Change permissions for entrypoint and make sure dataset volume mount parent directories exists
RUN chmod +x ${WORKDIR}/entrypoint.sh \
    && for d in ${DATASET_DIRECTORIES}; do mkdir -p /dmod/datasets/${d}; done \
    && pushd /dmod/bin \
    # NOTE use of `ln -sf`. \
    && ( ( stat ngen-parallel && ln -sf ngen-parallel ngen ) || ( stat ngen-serial && ln -sf ngen-serial ngen ) ) \
    && popd

WORKDIR ${WORKDIR}
ENV PATH=${WORKDIR}:$PATH
ENTRYPOINT ["entrypoint.sh"]
CMD [""]

################################################################################################################
################################################################################################################
##### Calibration ngen-cal worker image build stage
FROM ngen_worker AS ngen_cal_worker

ARG NGEN_CAL_BRANCH
ARG NGEN_CAL_COMMIT

# Overwrite the ngen entrypoint script from the parent stage, which is already set up with ENTRYPOINT
COPY --chown=${USER:?} ngen_cal_entrypoint.sh ${WORKDIR:?}/entrypoint.sh

USER root
# Try NGEN_CAL_COMMIT, if not set or empty, use NGEN_CAL_BRANCH
RUN pip install --no-cache-dir "git+https://github.com/noaa-owp/ngen-cal@${NGEN_CAL_COMMIT:-${NGEN_CAL_BRANCH}}#egg=ngen_cal&subdirectory=python/ngen_cal"

USER ${USER}
RUN chmod +x ${WORKDIR}/entrypoint.sh
