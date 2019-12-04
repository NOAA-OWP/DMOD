#!/bin/bash

# Hack docker socket permissions
# DO NOT DO THIS, IT CHANGES THE OWNERSHIP ON THE HOST!!!
# sudo chown mpi:mpi /var/run/docker.sock
# INSTEAD, simply run the code that relies on the docker socket via sudo
#
## sudo python3 scheduler.py

cd ..
sudo python3 -m scheduler.src.scheduler
cd scheduler
mv ../hostfile .
sudo chown mpi:mpi hostfile
#
# cd ..
# sudo python3 -m unittest discover -v > unittest_outfile
echo
echo "back from python3 scheduler.py"

# If run_option=2, run 2 domains, otherwise, skip the following block of codes
# For the moment, this is set manually in this script
run_option=0        # Also, set run_option = 1 in scheduler.py to run run the 2 domain case

if [ $run_option -eq 2 ]; then

  # The following codes are for running another copy of the domain.
  # Can be commented out if running only one copy which is handled through the scheduler.py code
  sleep 60

  # Some hackery to get things into workers correctly
  nwm_dir=/nwm
  domain_location=/nwm/domains
  run_dir=$domain_location/example_case1/NWM

  # temporary woker container name: "nwm_mpi-worker_tmp0"
  # should be made more general/systematic in future
  worker0=nwm_mpi-worker_tmp0
  src_dir=$domain_location/example_case/NWM

  # Using hostfile to determine the total number CPUs for the MPI processes
  total_cpus=0
  for host in `cat hostfile`; do
      cpus=`echo $host | cut -d ':' -f 2`
      ((total_cpus = total_cpus+$cpus))
  done

  exec_dir=/nwm/wrf_hydro_nwm_public/trunk/NDHMS/Run
  ssh $worker0 "cd $run_dir && cp $src_dir/hostfile . && /usr/local/bin/mpirun -f hostfile -n $total_cpus $exec_dir/wrf_hydro.exe"
fi

sudo /usr/sbin/sshd -D    # This command keeps the scheduler up
