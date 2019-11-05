FROM 127.0.0.1:5000/nwm-deps

ARG NWM_REPO_URL=https://github.com/NCAR/wrf_hydro_nwm_public.git
ARG NWM_BRANCH=master
ENV PATH "/nwm/wrf_hydro_nwm_public/trunk/NDHMS/Run:${PATH}"

RUN if [ "x$NWM_REPO_URL" = "x" ]; then NWM_REPO_URL="https://github.com/NCAR/wrf_hydro_nwm_public.git"; fi && \
    if [ "x$NWM_BRANCH" = "x" ]; then NWM_BRANCH=master; fi && \
    echo $NWM_REPO_URL && echo $NWM_BRANCH && \
    git clone --single-branch --branch $NWM_BRANCH $NWM_REPO_URL && \
    cd wrf_hydro_nwm_public/trunk/NDHMS && \
    ./configure 2 && \
    ./compile_offline_NoahMP.sh ./template/setEnvar.sh
USER root
RUN echo "export PATH=${PATH}" >> /etc/profile
USER ${USER}
WORKDIR /nwm/domains
