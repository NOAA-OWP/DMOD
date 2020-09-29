#!/bin/sh

# Wait a bit to make sure all service workers are up
sleep 15

req_id = $1
echo ${req_id}

cd ${WORKDIR}
domain_location=${WORKDIR}
tmp_domain=${WORKDIR}/data/tmp_${req_id}
mkdir -p $tmp_domain
ln -s $domain_location/data/$2/* $tmp_domain/

cd $tmp_domain

ngen ./data/$1/catchment_data.geojson "" ./data/$1/nexus_data.geojson "" ./data/$1/realization_config.json

echo 'ngen returned with a return value: ' $?
