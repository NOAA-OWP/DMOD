#!/bin/bash

cd /nwm
idx=0
for str in $@
do
    if [ $idx -eq 0 ]; then
        echo $str > hostfile
    else
        echo $str >> hostfile
    fi
    ((idx++))
done

# Prepare to run jobs
run_dir=/nwm/domains/example_case/NWM
cd $run_dir

idx=0
for str in $@
do
    if [ $idx -eq 0 ]; then
        echo $str > hostfile
    else
        echo $str >> hostfile
    fi
    ((idx++))
done

total_cpus=0
for host in `cat hostfile`; do
    cpus=`echo $host | cut -d ':' -f 2`
    ((total_cpus = total_cpus+$cpus))
done

# echo $total_cpus >> hostfile

/usr/local/bin/mpirun -f hostfile -n $total_cpus wrf_hydro.exe &

sudo /usr/sbin/sshd -D
