#!/bin/bash

docker build -f mgmt.dockerfile -t mgmt .

echo " "
echo "run the service"
docker-compose -f redis.yml up -d
# docker run -v /var/run/docker.sock:/var/run/docker.sock --network host mgmt
docker run -v /var/run/docker.sock:/var/run/docker.sock --network mpi-net mgmt
## docker service create --mount type=bind,source=/var/run/docker.sock,destination=/var/run/docker.sock --constraint 'node.role==manager' mgmt 
# docker exec -ti mgmt sudo /usr/sbin/sshd -D

echo " "
echo "list service"
docker service ls

