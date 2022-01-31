FROM alpine:3.15
# In case the main package repositories are down, use the alternative base image:
# FROM gliderlabs/alpine:3.12

ARG REPOS=""
ARG REQUIRE="sudo openssh bash"

ARG USER=mpi

ENV USER=${USER} USER_HOME=/home/${USER}
ENV SSHDIR=${USER_HOME}/.ssh
RUN apk update && apk upgrade \
    &&  if [ -n "${REPOS}" ]; then \
            apk add --repository ${REPOS} --no-cache ${REQUIRE}; \
        else \
            apk add --no-cache ${REQUIRE}; \
        fi \
    #### ADD DEFAULT USER #### \
    && adduser -D ${USER} \
    && echo "${USER}   ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers \
    && chown -R ${USER}:${USER} ${USER_HOME} \
    # # ------------------------------------------------------------ \
    # # Set up SSH Server \
    # # ------------------------------------------------------------ \
    # Add host keys \
    && cd /etc/ssh/ && ssh-keygen -A -N '' \
    # Config SSH Daemon \
    && sed -i "s/#PasswordAuthentication.*/PasswordAuthentication no/g" /etc/ssh/sshd_config \
    && sed -i "s/#PermitRootLogin.*/PermitRootLogin no/g" /etc/ssh/sshd_config \
    && sed -i "s/#AuthorizedKeysFile/AuthorizedKeysFile/g" /etc/ssh/sshd_config \
    # Unlock non-password USER to enable SSH login \
    && passwd -u ${USER} \
    # Set up user's public and private keys \
    &&  mkdir -p ${SSHDIR} \
    # Default ssh config file that skips (yes/no) question when first login to the host \
    && echo "StrictHostKeyChecking no" > ${SSHDIR}/config
# This file can be overwritten by the following onbuild step if ssh/ directory has config file

# # ------------------------------------------------------------
# # ONBUILD (require ssh/ directory in the build context)
# # ------------------------------------------------------------
USER root

COPY ssh ${SSHDIR}/

RUN cat ${SSHDIR}/*.pub >> ${SSHDIR}/authorized_keys \
    && chmod -R 600 ${SSHDIR}/* \
    && chown -R ${USER}:${USER} ${SSHDIR}

# Switch back to default user when continue the build process
USER ${USER}
