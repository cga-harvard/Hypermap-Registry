#!/bin/sh

DJANGO_DIR=/home/ubuntu/HHypermap
VIRTUAL_ENV=/home/ubuntu/venvs/env

# Activate the virtual environment.
. $VIRTUAL_ENV/bin/activate

# Read env variables
. $DJANGO_DIR/env_vars

cd $DJANGO_DIR
celery -A hypermap worker -l info
