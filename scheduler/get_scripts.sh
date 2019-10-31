#!/bin/bash

# server=`hostname`
server=nwm-_scheduler
echo $server >> ping_test

sudo ping -c1 -W1 -q $server &>/dev/null

status=$( echo $? )
# echo $status
if [[ $status == 0 ]] ; then
    echo "Connection success!" >> ping_test
else
    echo "Connection failure" >> ping_test
fi

# Remote copy hostfile
i=0
while [ $i -lt 10 ]
do
    scp mpi@nwm-_scheduler:/nwm/hostfile /nwm/domains/example_case/Gridded
    status=$( echo $? )
    sleep 5

    if [[ $status == 0 ]] ; then
        echo "Copy Completed!" >> ping_test
        break
    else
        continue
    fi
    ((i++))
done

# Prepare to run jobs
run_dir=/nwm/domains/example_case/Gridded
cd $run_dir

total_cpus=0
for host in `cat hostfile`; do
    cpus=`echo $host | cut -d ':' -f 2`
    ((total_cpus = total_cpus+$cpus))
done

/usr/local/bin/mpirun -f hostfile -n $total_cpus ./wrf_hydro.exe &

