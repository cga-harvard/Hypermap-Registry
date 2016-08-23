#!/usr/bin/env python
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hypermap.settings')

from django.conf import settings  # noqa

app = Celery(settings.CELERY_DEFAULT_EXCHANGE)

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
