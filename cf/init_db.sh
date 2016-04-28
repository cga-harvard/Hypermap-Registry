#!/bin/sh
echo "------ Create database tables ------"
python hypermap/manage.py syncdb --noinput

echo "------ create default admin user ------"
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@admin.admin', 'admin')" | python hypermap/manage.py shell

echo "------ Running server instance -----"
python hypermap/manage.py runserver --insecure 0.0.0.0:$PORT
