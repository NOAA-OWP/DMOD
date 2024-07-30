#!/bin/bash

python3 runner.py &
python3 manage.py runserver 127.0.0.1:9431

exit $?
