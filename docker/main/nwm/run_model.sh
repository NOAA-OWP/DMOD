#!/bin/bash

while [ ${#} -gt 0 ]; do
    case "${1}" in
# TODO: most likely, we are eventually going to need these available too for jobs to actually function
#        --config-dataset)
#            CONFIG_DATASET_NAME="${2:?}"
#            shift
#            ;;
#        --output-dataset)
#            OUTPUT_DATASET_NAME="${2:?}"
#            shift
#            ;;
        --host-string)
            # MPI host string; i.e., comma delimited hostnames and per-host cpu counts (e.g. hostname:N,hostname:M)
            MPI_HOST_STRING="${2:?}"
            shift
            ;;
        --job-id)
            # A unique id for the job being executed
            JOB_ID="${2:?}"
            shift
            ;;
        --node-count)
            # The number of distinct hosts/nodes in the job (different from cpu count)
            MPI_NODE_COUNT="${2:?}"
            shift
            ;;
        --worker-index)
            # Optional index of the distributed job/s this entrypoint is responsible for
            # if the idx is 0, this is the main MPI worker responsible for launching the job, otherwise, it is a worker
            # that simply needs to start the SSH daemon and wait
            WORKER_INDEX="${2:?}"
            shift
            ;;
    esac
    shift
done

if [ "x$WORKER_INDEX" != "x" ] && [ $WORKER_INDEX == "0" ]
then
echo "Starting SSH daemon on main worker"
sudo /usr/sbin/sshd -D &

MPI_NODE_COUNT=$((MPI_NODE_COUNT + 0))
#Setup the runtime paths
cd ${WORKDIR}
domain_location=${WORKDIR}/domains
output_dir=${WORKDIR}/output
#Make a temp working dir
# TODO: this needs to be the output dataset
tmp_domain=$output_dir/tmp_${JOB_ID}
mkdir -p $tmp_domain
#Link the static domain and runtime tables to the working dir
ln -s $domain_location/* $tmp_domain/
ln -s ${WORKDIR}/*.TBL $tmp_domain/
cd $tmp_domain

# write hoststring to file
echo $MPI_HOST_STRING >> hostfile

total_cpus=0
#Determine total CPUS and make sure hosts are running ssh
for host in `cat hostfile`; do
    cpus=`echo $host | cut -d ':' -f 2`
    host_name=`echo $host | cut -d ':' -f 1`
    ((total_cpus = total_cpus+$cpus))
    #Make sure all hosts are reachable, this also covers localhost
    until ssh -q $host_name exit >/dev/null 2>&1; do :; done
done

echo "Running MPI with $total_cpus"
#execute the MPI model
/usr/local/bin/mpirun -f hostfile -n $total_cpus wrf_hydro.exe
#Hold the return value as exit status after cleanup
mpi_rtn_val=$?
echo 'mpirun returned with a return value: ' $mpi_rtn_val
echo $(date)
#Clean up any links in output mount
find . -maxdepth 1 -type l -delete
#Remove hostfile
rm hostfile
exit $mpi_rtn_val

else
  echo "Starting SSH daemon, waiting for main job"
  sudo /usr/sbin/sshd -D
fi
