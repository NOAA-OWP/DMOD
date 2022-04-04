# FROM alpine
FROM 127.0.0.1:5000/nwm-base
USER root

# RUN apk update && apk add --no-cache openssl python3 py3-pip && rm -rf /var/cache/apk/* && alias pip=pip3  python=python3
RUN apk update && apk add --no-cache openssl python3 python3-dev bash && rm -rf /var/cache/apk/* && alias python=python3 && pip3 install --no-cache-dir --upgrade pip
# RUN apk add --update py-pip


# RUN apk update && apk add --no-cache openssl && rm -rf /var/cache/apk/*
RUN pip install --upgrade pip
RUN pip install docker
RUN pip install redis
RUN pip install Faker
RUN pip install pyyaml
RUN mkdir -p /nwm/monitor/src
RUN mkdir -p /nwm/monitor/utils
RUN mkdir -p /nwm/monitor/test
RUN chown -R mpi:mpi /nwm

USER ${USER}
WORKDIR /nwm/monitor
RUN mkdir -p ~/.ssh && printf "Host *\n        ServerAliveInterval 300\n        ServerAliveCountMax 2\n" >> ~/.ssh/config
COPY --chown=mpi:mpi conf/redis.conf /usr/local/etc/redis/redis.conf
COPY --chown=mpi:mpi utils/* /nwm/monitor/utils/
COPY --chown=mpi:mpi lib/ /nwm/monitor/lib/
COPY --chown=mpi:mpi src/* /nwm/monitor/src/
#COPY --chown=mpi:mpi src/image_and_domain.yaml /nwm/
COPY --chown=mpi:mpi entry.sh /nwm/monitor
COPY --chown=mpi:mpi __init__.py /nwm/monitor
# Unittest
# COPY --chown=mpi:mpi test/test_scheduler.py /nwm/test
# COPY --chown=mpi:mpi test/__init__.py /nwm/test
# COPY --chown=mpi:mpi test/* /nwm/test/

# TODO: when image tagging/versioning is improved, look at keeping this in a "debug" image only
# Copy this to have access to debugging pydevd egg
COPY --from=sources /dmod /dmod_src
RUN if [ -e /dmod_src/python/pydevd-pycharm.egg ]; then mv /dmod_src/python/pydevd-pycharm.egg /. ; fi \
    && rm -rf /dmod_src

CMD ["/bin/bash"]
