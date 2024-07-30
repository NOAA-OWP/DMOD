#!/bin/bash

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

sudo /usr/sbin/sshd -D
