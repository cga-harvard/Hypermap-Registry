#!/bin/sh

echo "------ Running celery instance -----"
celery worker --app=hypermap.celeryapp:app -B -l INFO
