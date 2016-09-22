#!/usr/bin/env python

import os
import sys


if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hypermap.settings')

    from django.conf import settings

    sys.path.insert(0, os.path.join(settings.PROJECT_DIR, "..", "libs", "django-mapproxy"))
    sys.path.insert(0, os.path.join(settings.PROJECT_DIR, "..", "libs", "mapproxy"))
    import djmp, mapproxy

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
