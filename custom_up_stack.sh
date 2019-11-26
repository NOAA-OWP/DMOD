#!/bin/bash
#Not sure the registry is directly tied to the stack...
#echo "Deploying registry"
#docker stack deploy --compose-file docker-registry.yml nwm
echo "Building images"
docker build -t 127.0.0.1:5000/mgmt ./scheduler
# docker-compose -f docker-build-custom.yml build
# if [ "$1" = "update" ]; then
#     docker-compose -f docker-build-custom.yml build --no-cache nwm
# fi
echo "Pushing images to registry"
docker-compose -f docker-build-custom.yml push
#echo "Deploying NWM stack"
docker stack deploy --compose-file docker-deploy-custom.yml nwm-${NWM_NAME}
