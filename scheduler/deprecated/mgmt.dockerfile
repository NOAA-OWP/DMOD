FROM alpine
RUN apk update && apk add --no-cache openssl && rm -rf /var/cache/apk/*

FROM python:3

# RUN apk update && apk add --no-cache openssl && rm -rf /var/cache/apk/*
RUN pip install --upgrade pip
RUN pip install docker
RUN pip install redis
RUN pip install Faker

COPY conf/redis.conf /usr/local/etc/redis/redis.conf
COPY generate.py /
COPY nwmaas.scheduler.utils/* /nwmaas.scheduler.utils/
COPY parsing_nested.py /
COPY request.py /
COPY scheduler.py /
COPY entry.sh /

CMD ["/bin/bash", "entry.sh"]
# CMD ["python3", "scheduler.py"]
