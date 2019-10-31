#!/bin/bash

# Hack docker socket permissions
# DO NOT DO THIS, IT CHANGES THE OWNERSHIP ON THE HOST!!!
# sudo chown mpi:mpi /var/run/docker.sock
# INSTEAD, simply run the code that relies on the docker socket via sudo
#
# sudo python3 scheduler.py
#
cd ..
sudo python3 -m unittest discover -v > unittest_outfile
echo
echo "back from python3 scheduler.py"

sleep 30

# Some hackery to get things into workers correctly
# workers=`cat hostfile`
# master=`cat masterfile`

nwm_dir=/nwm
domain_location=/nwm/domains
run_dir=$domain_location/example_case/Gridded
domain_dir=$run_dir/DOMAIN
restart_dir=$run_dir/RESTART
# ref_dir=$run_dir/referenceSim
# obs_dir=$domain_dir/nudgingTimeSliceObs

#ssh -t $master "sudo cp /nwm/wrf_hydro_nwm_public/trunk/NDHMS/Run/*.TBL $run_dir"


# ssh $master "cd $run_dir && /usr/local/bin/mpirun -n 2 -hosts nwm_mpi-worker_tmp0 ./wrf_hydro.exe &" &

# ssh $master "cd $run_dir && /usr/local/bin/mpirun -n 2 -hosts nwm_mpi-worker_tmp0,nwm_mpi-worker_tmp1 ./wrf_hydro.exe &" &
# run_dir1=$domain_location/example_case1/Gridded
# ssh $master "cd $run_dir1 && /usr/local/bin/mpirun -n 2 -hosts nwm_mpi-worker_tmp0,nwm_mpi-worker_tmp1 ./wrf_hydro.exe"

# scp hostfile  mpi@$master:$domain_location/example_case/Gridded
# ssh $master "cd $run_dir && /usr/local/bin/mpirun -f hostfile -n $total_cpus ./wrf_hydro.exe"
sudo /usr/sbin/sshd -D    # This command keeps the scheduler up
