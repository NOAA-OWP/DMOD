#!/bin/bash

# Hack docker socket permissions
# DO NOT DO THIS, IT CHANGES THE OWNERSHIP ON THE HOST!!!
# sudo chown mpi:mpi /var/run/docker.sock
# INSTEAD, simply run the code that relies on the docker socket via sudo
#
## sudo python3 scheduler.py

cd ..
# sudo python3 -m scheduler.src.scheduler
sleep 10
sudo python3 -m monitor.src.que_monitor

# sudo python3 -m unittest discover -v > unittest_outfile
echo
echo "back from python3 que_monitor.py"

sudo /usr/sbin/sshd -D    # This command keeps the scheduler up
