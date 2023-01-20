ARG DOCKER_INTERNAL_REGISTRY

FROM ${DOCKER_INTERNAL_REGISTRY}/ngen:latest

ARG WORKDIR=/ngen
ARG USER=mpi
ARG NGEN_CAL_BRANCH=master
ARG NGEN_CAL_COMMIT

ENV USER=${USER} USER_HOME=/home/${USER}

WORKDIR ${WORKDIR}
USER ${USER}

# try NGEN_CAL_COMMIT, if not set or empty, use NGEN_CAL_BRANCH
RUN pip install "git+https://github.com/noaa-owp/ngen-cal@${NGEN_CAL_COMMIT:-${NGEN_CAL_BRANCH}}#egg=ngen_cal&subdirectory=python/ngen_cal"

COPY --chown=${USER} entrypoint.sh ${WORKDIR}

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
    # NOTE use of `ln -sf`. \
    && ( ( stat ngen-parallel && ln -sf ngen-parallel ngen ) || ( stat ngen-serial && ln -sf ngen-serial ngen ) ) \
    && popd 

ENV PATH=${WORKDIR}:$PATH
ENTRYPOINT ["entrypoint.sh"]
CMD [""]
