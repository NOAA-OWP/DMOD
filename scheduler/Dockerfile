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
RUN mkdir -p /nwm/scheduler
RUN mkdir -p /nwm/scheduler/utils
RUN mkdir -p /nwm/test
RUN chown -R mpi:mpi /nwm

USER ${USER}
WORKDIR /nwm/scheduler
RUN mkdir -p ~/.ssh && printf "Host *\n        ServerAliveInterval 300\n        ServerAliveCountMax 2\n" >> ~/.ssh/config
# USER mpi
COPY --chown=mpi:mpi conf/redis.conf /usr/local/etc/redis/redis.conf
COPY --chown=mpi:mpi generate.py /nwm/scheduler
COPY --chown=mpi:mpi utils/* /nwm/scheduler/utils/
COPY --chown=mpi:mpi parsing_nested.py /nwm/scheduler
COPY --chown=mpi:mpi request.py /nwm/scheduler
COPY --chown=mpi:mpi scheduler.py /nwm/scheduler
COPY --chown=mpi:mpi entry.sh /nwm/scheduler
COPY --chown=mpi:mpi distribute_domain.sh /nwm/scheduler
COPY --chown=mpi:mpi run_domain.sh /nwm/scheduler
COPY --chown=mpi:mpi run.sh /nwm/scheduler
COPY --chown=mpi:mpi __init__.py /nwm/scheduler
# Unittest
# COPY --chown=mpi:mpi test/test_scheduler.py /nwm/test
# COPY --chown=mpi:mpi test/__init__.py /nwm/test
COPY --chown=mpi:mpi test/* /nwm/test/

CMD ["/bin/bash"]
# CMD ["/bin/bash", "entry.sh"]
# CMD ["python3", "scheduler.py"]
