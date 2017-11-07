from __future__ import absolute_import

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celeryapp import app as celery_app  # noqa

__version__ = '0.3.12'
__description__ = 'hhypermap'
