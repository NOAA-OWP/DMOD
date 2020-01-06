#!/bin/bash
#Some hackery to get things into workers correctly
workers=`cat hostfile`
# master=`cat masterfile`

nwm_dir=/nwm
domain_location=/nwm/domains
run_dir=$domain_location/example_case/Gridded
domain_dir=$run_dir/DOMAIN
restart_dir=$run_dir/RESTART
# ref_dir=$run_dir/referenceSim
# obs_dir=$domain_dir/nudgingTimeSliceObs

#ssh -t $master "sudo cp /nwm/wrf_hydro_nwm_public/trunk/NDHMS/Run/*.TBL $run_dir"

worker_id=0
total_cpus=0
for host in `cat hostfile`; do
    hostname=`echo $host | cut -d ':' -f 1`
    cpus=`echo $host | cut -d ':' -f 2`
    ((total_cpus = total_cpus+$cpus))
    if [ $worker_id -eq 0 ]
    then
        master=$hostname
        # ssh -t $master "sed -i 's/RESTART_FILE/! RESTART_FILE/' /nwm/domains/example_case/Gridded/hydro.namelist"
        ssh $master "sed -i 's/RESTART_FILE/! RESTART_FILE/' /nwm/domains/example_case/Gridded/hydro.namelist"
        # ssh $master "mkdir -p $domain_location/example_case1"
        ssh $master "mkdir -p $domain_location/example_case1/Gridded"
        # Eventually need to put all the files in a file listing all the file names and use a do loop
        ssh $master "ln -s $domain_location/example_case/Gridded/DOMAIN $domain_location/example_case1/Gridded"
        ssh $master "ln -s $domain_location/example_case/Gridded/FORCING $domain_location/example_case1/Gridded"
        ssh $master "ln -s $domain_location/example_case/Gridded/RESTART $domain_location/example_case1/Gridded"
        ssh $master "ln -s $domain_location/example_case/Gridded/referenceSim $domain_location/example_case1/Gridded"
        ssh $master "ln -s $domain_location/example_case/Gridded/CHANPARM.TBL $domain_location/example_case1/Gridded"
        ssh $master "ln -s $domain_location/example_case/Gridded/GENPARM.TBL $domain_location/example_case1/Gridded"
        ssh $master "ln -s $domain_location/example_case/Gridded/HYDRO.TBL $domain_location/example_case1/Gridded"
        ssh $master "ln -s $domain_location/example_case/Gridded/MPTABLE.TBL $domain_location/example_case1/Gridded"
        ssh $master "ln -s $domain_location/example_case/Gridded/SOILPARM.TBL $domain_location/example_case1/Gridded"
        ssh $master "ln -s $domain_location/example_case/Gridded/croton_frxst_pts_csv.csv $domain_location/example_case1/Gridded"
        ssh $master "ln -s $domain_location/example_case/Gridded/hydro.namelist $domain_location/example_case1/Gridded"
        ssh $master "ln -s $domain_location/example_case/Gridded/namelist.hrldas $domain_location/example_case1/Gridded"
        ssh $master "ln -s $domain_location/example_case/Gridded/wrf_hydro.exe $domain_location/example_case1/Gridded"
    else
        worker=$hostname
        scp -r mpi@$master:$domain_location/example_case mpi@$worker:/nwm
        ssh $worker "sed -i 's/RESTART_FILE/! RESTART_FILE/' /nwm/domains/example_case/Gridded/hydro.namelist"
        # ssh $worker "mkdir -p $domain_location/example_case1"
        ssh $worker "mkdir -p $domain_location/example_case1/Gridded"
        # Eventually need to put all the files in a file listing all the file names and use a do loop
        ssh $worker "ln -s $domain_location/example_case/Gridded/DOMAIN $domain_location/example_case1/Gridded"
        ssh $worker "ln -s $domain_location/example_case/Gridded/FORCING $domain_location/example_case1/Gridded"
        ssh $worker "ln -s $domain_location/example_case/Gridded/RESTART $domain_location/example_case1/Gridded"
        ssh $worker "ln -s $domain_location/example_case/Gridded/referenceSim $domain_location/example_case1/Gridded"
        ssh $worker "ln -s $domain_location/example_case/Gridded/CHANPARM.TBL $domain_location/example_case1/Gridded"
        ssh $worker "ln -s $domain_location/example_case/Gridded/GENPARM.TBL $domain_location/example_case1/Gridded"
        ssh $worker "ln -s $domain_location/example_case/Gridded/HYDRO.TBL $domain_location/example_case1/Gridded"
        ssh $worker "ln -s $domain_location/example_case/Gridded/MPTABLE.TBL $domain_location/example_case1/Gridded"
        ssh $worker "ln -s $domain_location/example_case/Gridded/SOILPARM.TBL $domain_location/example_case1/Gridded"
        ssh $worker "ln -s $domain_location/example_case/Gridded/croton_frxst_pts_csv.csv $domain_location/example_case1/Gridded"
        ssh $worker "ln -s $domain_location/example_case/Gridded/hydro.namelist $domain_location/example_case1/Gridded"
        ssh $worker "ln -s $domain_location/example_case/Gridded/namelist.hrldas $domain_location/example_case1/Gridded"
        ssh $worker "ln -s $domain_location/example_case/Gridded/wrf_hydro.exe $domain_location/example_case1/Gridded"
    fi
    ((worker_id += 1))
done

# wait for the scp operation to finish
sleep 20s

# ssh $master "cd $run_dir && /usr/local/bin/mpirun -n 4 -hosts nwm_mpi-worker_tmp0,nwm_mpi-worker_tmp1 ./wrf_hydro.exe &" &
ssh $master "cd $run_dir && /usr/local/bin/mpirun -n 2 -hosts nwm_mpi-worker_tmp0 ./wrf_hydro.exe &" &
# run_dir1=$domain_location/example_case1/Gridded
# ssh $master "cd $run_dir1 && /usr/local/bin/mpirun -n 2 -hosts nwm_mpi-worker_tmp0,nwm_mpi-worker_tmp1 ./wrf_hydro.exe"

# scp hostfile  mpi@$master:$domain_location/example_case/Gridded
# ssh $master "cd $run_dir && /usr/local/bin/mpirun -f hostfile -n $total_cpus ./wrf_hydro.exe"


# for worker in $workers; do
#      #TOTAL HACK FOR PERMISSIONS ON WORKER...as well as initial file dissemenation
#      #Would be better for all nodes to mount a common file system???
#      ssh -t $worker "mkdir -p $domain_dir $restart_dir $obs_dir" 
#      scp $master:$run_dir/namelist.hrldas $worker:$run_dir
#      scp $master:$run_dir/hydro.namelist $worker:$run_dir
#      scp $master:$domain_dir/wrfinput_d01_1km.nc $worker:$domain_dir
#      scp $master:$domain_dir/LAKEPARM_NHDPLUS.nc $worker:$domain_dir
#      #TODO/FIXME verify that RESTART* is needed...may not be
#      scp $master:"$restart_dir/HYDRO_RST.* $restart_dir/RESTART*" $worker:$restart_dir
      
#      scp $master:$run_dir/*.TBL $worker:$run_dir
#      scp $master:"$obs_dir/*" $worker:$obs_dir
# done
