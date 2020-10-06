#!/bin/bash
# $1 will have the number of nodes associated with this run
# $2 will have the host string in MPI form, i.e. hostname:N, hostname:M
# $3 will have the unique job id
# $4 is optional, and if set is the index of the distributed job/s this entrypoint is responsible for
# if the idx is 0, this is the main MPI worker responsible for launching the job, otherwise, it is a worker
# that simply needs to start the SSH daemon and wait

if [ "x$4" != "x" ] && [ $4 == "0" ]
then
echo "Starting SSH daemon on main worker"
sudo /usr/sbin/sshd -D &

num_hosts=$1
num_hosts=$((num_hosts + 0))
req_id=$3
#Setup the runtime paths
cd ${WORKDIR}
domain_location=${WORKDIR}/domains
output_dir=${WORKDIR}/output
#Make a temp working dir
tmp_domain=$output_dir/tmp_${req_id}
mkdir -p $tmp_domain
#Link the static domain and runtime tables to the working dir
ln -s $domain_location/* $tmp_domain/
ln -s ${WORKDIR}/*.TBL $tmp_domain/
cd $tmp_domain

# write hoststring to file
echo $2 >> hostfile

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
