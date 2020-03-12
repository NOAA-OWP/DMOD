#!/bin/bash

cd /nwm

domain_location=/nwm/domains
tmp_domain=/nwm/domains/tmp_$(hostname)
mkdir -p $tmp_domain

num_hosts=$1
num_hosts=$((num_hosts + 0))

idx=0
for str in $@
do
    if [ $idx -eq 0 ]; then
        # echo $str >> hostfile1
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

ln -s ${run_domain_dir}/* $tmp_domain/
run_dir=$tmp_domain
cd $run_dir
cp /nwm/hostfile .

total_cpus=0
for host in `cat hostfile`; do
    cpus=`echo $host | cut -d ':' -f 2`
    ((total_cpus = total_cpus+$cpus))
done

echo 'starting mpirun'
echo $(date)
/usr/local/bin/mpirun -f hostfile -n $total_cpus wrf_hydro.exe
mpi_rtn_val=$?
echo 'mpirun returned with a return value: ' $mpi_rtn_val
echo $(date)
sleep 30
# exit $mpi_rtn_val	# Running this command will stop the container
sudo /usr/sbin/sshd -D 
