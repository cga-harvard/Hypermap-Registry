#!/bin/sh

DJANGO_DIR=/home/ubuntu/Hypermap-Registry
VIRTUAL_ENV=/home/ubuntu/env

# Activate the virtual environment.
. $VIRTUAL_ENV/bin/activate

# Read env variables
. home/ubuntu/env_vars

cd $DJANGO_DIR
celery -A hypermap worker -l info
