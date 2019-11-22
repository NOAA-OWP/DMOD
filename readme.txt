Docker Notes:
must enable ip.v4.forward (for swarm???)

insecure registries:
127.0.0.1:localhost

docker stack depoly docker-registry.yml nwm
docker-compose -f docker-build.yml build
docker-compose -f docker-build.yml push
docker stack deploy --compose-file docker-deploy.yml nwm


NEED TO ENSURE MOUNTED DOMAIN VOLUME ON MASTER IS CHOWNED AT LEAST ONCE chown -R mpi /nwm/domains

ALSO: if domain names/locations change, you may have to edit the entry script for scheduler to copy
the required files to all workers.  MPI will throw strange errors if the working directory on master
doesn't exist on the wokers.  And wrf_hydro will die if it can't find certain files for reading everywhere.



To deploy a custom fork/branch of the code on a new stack, use the following environment variables:
NWM_NAME=<name of NWM images>
NWM_REPO_URL=<git URL of the code to use, defaults to upstream NCAR>
NWM_BRANCH=<branch name to use, defaults to master>
I.E.
NWM_NAME=persistence-test NWM_REPO_URL=https://github.com/jdmattern-noaa/wrf_hydro_nwm_public NWM_BRANCH=persistence-development ./custom_up_stack.sh
Or to build lastet master
NWM_NAME=master ./custom_up_stack.sh

If you already have the stack built, and simply need to pull new NWM code, pass the keyword update to the script as the
first positional arg, i.e.
NWM_NAME=master ./custom_up_stack.sh update
