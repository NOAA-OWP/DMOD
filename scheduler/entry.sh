#!/bin/bash

# Hack docker socket permissions
# DO NOT DO THIS, IT CHANGES THE OWNERSHIP ON THE HOST!!!
# sudo chown mpi:mpi /var/run/docker.sock
# INSTEAD, simply run the code that relies on the docker socket via sudo
#
## sudo python3 scheduler.py

sudo /usr/sbin/sshd -D &    # This command keeps the scheduler up

sudo python3 -u service.py #TODO add args for running dev tests in service.py

