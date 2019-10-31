#!/bin/bash

# service_id=`docker service ls | grep cpu_test |cut -d ' ' -f 1`
# docker service rm service_id

docker service rm `docker service ls | grep nwm_mpi-worker_ |cut -d ' ' -f 1`
docker service rm  nwm-_scheduler
docker-compose -f redis.yml down
# docker service rm `docker service ls | grep nwm_mpi-worker_tmp |cut -d ' ' -f 1`
# docker service rm `docker service ls | grep zen_kilby |cut -d ' ' -f 1`
# docker service rm `docker service ls | grep mgmt:latest |cut -d ' ' -f 1`
