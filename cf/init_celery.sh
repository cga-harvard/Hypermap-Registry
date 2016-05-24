#!/bin/sh

echo "------ Running celery instance -----"
echo "------ Running server to pass health check -----"
python manage.py runserver --insecure 0.0.0.0:$PORT & celery worker --app=hypermap.celeryapp:app -B -l INFO
