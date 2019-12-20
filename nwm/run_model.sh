#!/bin/bash
cd /nwm

domain_location=/nwm/domains
tmp_domain=/nwm/domains/tmp_$(hostname)
mkdir -p $tmp_domain
ln -s $domain_location/example_case/NWM/* $tmp_domain/
run_dir=$tmp_domain

cd $run_dir


#Prepare to run jobs

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
cd /nwm
#sleep 3
#rm -rf $tmp_domain
#exit 0
sudo /usr/sbin/sshd -D 

