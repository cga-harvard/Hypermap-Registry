#!/bin/sh

DJANGO_DIR=/home/ubuntu/Hypermap-Registry
VIRTUAL_ENV=/home/ubuntu/env

# Activate the virtual environment.
. $VIRTUAL_ENV/bin/activate

# Read env variables
. env_vars

cd $DJANGO_DIR
celery -A hypermap beat -l info -S django --pidfile= -l info -s /tmp/celerybeat-schedule
