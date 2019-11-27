# FROM alpine
#FROM 127.0.0.1:5000/nwm-base
FROM python:3.7-alpine
#USER root

# RUN apk update && apk add --no-cache openssl python3 py3-pip && rm -rf /var/cache/apk/* && alias pip=pip3  python=python3
#RUN apk update && apk add --no-cache openssl python3 python3-dev bash && rm -rf /var/cache/apk/* && alias python=python3 && pip3 install --no-cache-dir --upgrade pip
RUN apk update && apk add --no-cache openssl bash && rm -rf /var/cache/apk/* && alias python=python3 && pip3 install --no-cache-dir --upgrade pip

# RUN apk add --update py-pip


# RUN apk update && apk add --no-cache openssl && rm -rf /var/cache/apk/*
RUN pip install --upgrade pip
RUN pip install docker
RUN pip install redis
RUN pip install Faker
RUN pip install websockets
RUN mkdir -p /nwm/scheduler/src
RUN mkdir -p /nwm/scheduler/utils
RUN mkdir -p /nwm/scheduler/test
RUN mkdir -p /nwm/communication
#RUN chown -R mpi:mpi /nwm

#USER ${USER}
WORKDIR /nwm/scheduler
RUN mkdir -p ~/.ssh && printf "Host *\n        ServerAliveInterval 300\n        ServerAliveCountMax 2\n" >> ~/.ssh/config
# USER mpi
COPY conf/redis.conf /usr/local/etc/redis/redis.conf
# COPY --chown=mpi:mpi generate.py /nwm/scheduler/src
COPY utils/* /nwm/scheduler/utils/
COPY src/* /nwm/scheduler/src/
COPY entry.sh /nwm/scheduler
COPY distribute_domain.sh /nwm/scheduler
COPY run_domain.sh /nwm/scheduler
COPY run.sh /nwm/scheduler
COPY __init__.py /nwm/scheduler
COPY service.py /nwm/scheduler
COPY communication/* /nwm/communication/ 
# Unittest
# COPY --chown=mpi:mpi test/test_scheduler.py /nwm/test
# COPY --chown=mpi:mpi test/__init__.py /nwm/test
# COPY --chown=mpi:mpi test/* /nwm/test/

#CMD ["/bin/bash"]
# CMD ["/bin/bash", "entry.sh"]
# CMD ["python3", "scheduler.py"]
CMD ["python3", "service.py"]
