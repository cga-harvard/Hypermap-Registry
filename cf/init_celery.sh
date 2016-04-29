#!/bin/sh

echo "------ Running celery instance -----"
echo "------ Running server to pass health check -----"
python hypermap/manage.py runserver --insecure 0.0.0.0:$PORT & python hypermap/manage.py celery -A hypermap worker -B -l INFO