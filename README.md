# HyperMap

## Aggregator

Create a periodic task using the Django admin, to run the process.

In a development environment run the worker process like this:

  ./manage.py celery -A hypermap worker -B -l info
