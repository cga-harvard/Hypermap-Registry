#!/bin/sh
echo "------ Create database tables ------"
python manage.py migrate auth
python manage.py syncdb --noinput
python manage.py collectstatic --noinput

echo "------ create default admin user ------"
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@admin.admin', 'admin')" | python manage.py shell

echo "------ Running server instance -----"
python manage.py runserver --insecure 0.0.0.0:$PORT
