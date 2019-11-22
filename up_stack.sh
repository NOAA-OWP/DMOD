#!/bin/bash
echo "Deploying registry"
docker stack deploy --compose-file docker-registry.yml nwm
echo "Building images"
docker-compose -f docker-build.yml build
echo "Pushing images to registry"
docker-compose -f docker-build.yml push
echo "Deploying NWM stack"
docker stack deploy --compose-file docker-deploy.yml nwm
