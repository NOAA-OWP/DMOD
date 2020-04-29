#!/bin/bash

# Wait a bit to make sure all service workers are up
sleep 15

num_hosts=$1
num_hosts=$((num_hosts + 0))
idx=0
for str in $@
do
    if [ $idx -ne 0 ] && [ $idx -le $num_hosts ]; then
        name=`echo $str | cut -d ':' -f 1`
        req_id=`echo $name | cut -d '_' -f 4`
        #echo $req_id
    fi
    ((idx++))
done
echo ${req_id}

cd /nwm
domain_location=/nwm/domains
tmp_domain=/nwm/domains/tmp_${req_id}
mkdir -p $tmp_domain
ln -s $domain_location/example_case/NWM/* $tmp_domain/

run_dir=$tmp_domain
cd $run_dir

# Parsing host_str and write to hostfile
idx=0
for str in $@
do
    if [ $idx -eq 0 ]; then
        echo $str
    elif [ $idx -eq 1 ]; then
        echo $str > hostfile
    elif [ $idx -le $num_hosts ]; then
        echo $str >> hostfile
    else
        run_domain_dir=$str
    fi
    ((idx++))
done

total_cpus=0
for host in `cat hostfile`; do
    cpus=`echo $host | cut -d ':' -f 2`
    ((total_cpus = total_cpus+$cpus))
done

/usr/local/bin/mpirun -f hostfile -n $total_cpus wrf_hydro.exe
mpi_rtn_val=$?
echo 'mpirun returned with a return value: ' $mpi_rtn_val
echo $(date)
sleep 10    # wait to see the time interval before job being resubmitted
exit $mpi_rtn_val

sudo /usr/sbin/sshd -D 

