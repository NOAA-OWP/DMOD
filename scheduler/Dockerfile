# problem using the current registry (127.0.0.1:5000), apparently due to the ':'
# which Docker thinks is an invalid --from value in the multi-stage copy step
ARG docker_internal_registry
FROM ${docker_internal_registry}/nwmaas-py-sources as sources

FROM python:3.7-alpine
ARG comms_package_name

# RUN apk update && apk add --no-cache openssl python3 py3-pip && rm -rf /var/cache/apk/* && alias pip=pip3  python=python3
#RUN apk update && apk add --no-cache openssl python3 python3-dev bash && rm -rf /var/cache/apk/* && alias python=python3 && pip3 install --no-cache-dir --upgrade pip

COPY requirements.txt /nwm/scheduler/requirements.txt
COPY conf/redis.conf /usr/local/etc/redis/redis.conf
COPY utils/ /nwm/scheduler/utils/
COPY src/ /nwm/scheduler/src/
COPY entry.sh /nwm/scheduler/entry.sh
COPY distribute_domain.sh /nwm/scheduler/distribute_domain.sh
COPY run_domain.sh /nwm/scheduler/run_domain.sh
COPY run.sh /nwm/scheduler/run.sh
COPY __init__.py /nwm/scheduler/__init__.py
COPY service.py /nwm/scheduler/service.py
# TODO: parameterize this (especially the dest dir) here, in service.py if-main section, eventual __main__.py, and
# TODO:     anywhere else appropriate using env variables or some other mechanism
COPY ssl/scheduler/ /nwm/scheduler/ssl/scheduler/

# Copy custom built packages from external sources image
COPY --from=sources /DIST /DIST

WORKDIR /nwm/scheduler

RUN apk update \
    && apk add --no-cache openssl bash \
    && rm -rf /var/cache/apk/* \
    && alias python=python3 \
    && pip3 install --no-cache-dir --upgrade pip \
    # Install custom and generally available packages, starting with any custom from external source image \
    && pip3 install --no-cache-dir --find-links=/DIST/comms ${comms_package_name} \
    # After eventually installing all custom packages like this, clean up ... \
    && rm -r /DIST \
    # Then also pull in any other dependencies via pip \
    && pip install --no-cache-dir --requirement /nwm/scheduler/requirements.txt \
    && mkdir -p ~/.ssh \
    && printf "Host *\n        ServerAliveInterval 300\n        ServerAliveCountMax 2\n" >> ~/.ssh/config


# Unittest
# COPY --chown=mpi:mpi test/test_scheduler.py /nwm/test
# COPY --chown=mpi:mpi test/__init__.py /nwm/test
# COPY --chown=mpi:mpi test/* /nwm/test/

#CMD ["/bin/bash"]
# CMD ["/bin/bash", "entry.sh"]
# CMD ["python3", "scheduler.py"]
CMD ["python3", "service.py"]
