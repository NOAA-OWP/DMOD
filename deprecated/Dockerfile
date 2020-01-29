FROM nwm-mpich-base
RUN mkdir -p /nwm
WORKDIR /nwm
RUN git clone https://github.com/NCAR/wrf_hydro_nwm_public.git

WORKDIR wrf_hydro_nwm_public/trunk/NDHMS

RUN ./configure 2
RUN sudo ./compile_offline_NoahMP.sh ./template/setEnvar.sh

ENV PATH="/nwm/wrf_hydro_nwm_public/trunk/NDHMS/Run:${PATH}"
#Copy in some ssh keys
ENV SSHDIR ${USER_HOME}/.ssh

USER root
COPY ssh/ ${SSHDIR}/
RUN cat ${SSHDIR}/*.pub >> ${SSHDIR}/authorized_keys
RUN chmod -R 600 ${SSHDIR}/* && chown -R ${USER}:${USER} ${SSHDIR}
USER ${USER}
WORKDIR /nwm/domains
CMD /bin/bash
