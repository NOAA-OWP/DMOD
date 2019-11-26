ARG NETCDF_C_VERSION
ARG DOCKER_INTERNAL_REGISTRY_HOST
ARG DOCKER_INTERNAL_REGISTRY_PORT
FROM ${DOCKER_INTERNAL_REGISTRY_HOST}:${DOCKER_INTERNAL_REGISTRY_PORT}/nwm-deps:netcdf_${NETCDF_C_VERSION:-latest}
#Passing the ARG variables from compose via .env file will squash these defaults with empty strings
#Seems like the work around is to replicate the default values in the build env, or to check for
#empty and set to default as is shown commented out below.
ARG REPO_URL=https://github.com/NCAR/wrf_hydro_nwm_public.git
ARG BRANCH=master
ARG COMMIT
ENV PATH "/nwm/wrf_hydro_nwm_public/trunk/NDHMS/Run:${PATH}"

#RUN if [ "x$REPO_URL" = "x" ]; then REPO_URL="https://github.com/NCAR/wrf_hydro_nwm_public.git"; fi && \
#    if [ "x$NWM_BRANCH" = "x" ]; then NWM_BRANCH=master; fi && \
#    echo $NWM_REPO_URL && echo $NWM_BRANCH && \
RUN git clone --single-branch --branch $BRANCH $REPO_URL && \
    cd wrf_hydro_nwm_public/trunk/NDHMS && \
    if [ "x$COMMIT" != "x" ]; then git checkout $COMMIT; fi && \
    #git checkout 6fe9fa3 && \
    ./configure 2 && \
    ./compile_offline_NoahMP.sh ./template/setEnvar.sh
USER root
RUN echo "export PATH=${PATH}" >> /etc/profile
#Tried getting some low lever profiling tools into the containers, but the sys calls are black listed.
#RUN apk add elfutils-libelf --repository http://dl-cdn.alpinelinux.org/alpine/edge/main
#RUN apk add --update perf --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing
USER ${USER}
WORKDIR /nwm/domains
