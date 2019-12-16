#!/bin/bash

run_dir=/nwm/domains/example_case/Gridded
cd $run_dir

# copy hostfile from the manager node to worker node
scp mpi@nwm-_scheduler:/nwm/hostfile .

total_cpus=0
for host in `cat hostfile`; do
    cpus=`echo $host | cut -d ':' -f 2`
    ((total_cpus = total_cpus+$cpus))
done

echo "run_dir $run_dir" >> test_outfile
echo "total_cpus = $total_cpus" >> test_outfile

/usr/local/bin/mpirun -f hostfile -n $total_cpus ./wrf_hydro.exe &
