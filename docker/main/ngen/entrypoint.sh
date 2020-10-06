#!/bin/sh
# $1 will have the number of nodes associated with this run
# $2 will have the host string in MPI form, i.e. hostname:N, hostname:M
# $3 will have the unique job id

#Make sure we are in workdir
cd ${WORKDIR}
#This is the input location that image_and_domain.yaml specificies as the run time mount location
domain_location=/ngen/data
#This is the output location that image_and_domain.yaml specifices as the run time mount location
output_dir=/ngen/output
#Create a tmp dir based on the job id to dump output to
tmp_domain=$output_dir/tmp_$3
mkdir -p $tmp_domain
#Soft link the mounted static inputs
ln -s $domain_location $tmp_domain/
#cd to the tmp dir to run
cd $tmp_domain
#Execute the model on the linked data
ngen ./data/catchment_data.geojson "" ./data/nexus_data.geojson "" ./data/refactored_example_realization_config.json > std_out.log 2> std_err.log
#Capture the return value to use as service exit code
ngen_return=$?
echo 'ngen returned with a return value: ' $ngen_return
#Remove soft link, which will have the same name as the last element of domain_location path
unlink data
#Exit with the model's exit code
exit $ngen_return
