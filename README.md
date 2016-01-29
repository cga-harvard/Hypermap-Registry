# HHypermap Supervisor

## Introduction

HHypermap (Harvard Hypermap) Supervisor is an application that manages OWS, Esri REST, and other types of map service harvesting, and maintains uptime statistics for services and layers. When possible, layers will be cached by MapProxy. It is anticipated that other types of service such as WFS, WCS, and WPS will eventually be included. The application will be used by Harvard WorldMap to collect and manage remote layers. HHypermap Supervisor will publish to HHypermap Search (based on Lucene) which provides a fast search and visualization environment for spatio-temporal materials.   

## Setup

Easiest way to have an HHypermap instance up and running is to use Vagrant.

```
git clone git@github.com:cga-harvard/hypermap.git
cd hypermap/deploy
vagrant up
```

Wait for the instance to be provisioned (about 3/4 minutes).

Then connect to: 192.168.33.15 and your instance should be up and running.

Create a periodic task using the Django admin (login: admin/admin), to run the
process. Task that needs to be run is check_all_services.

## Development mode

You can use the same instance if you are a developer. Just run the Django
server in place of nginx and uwsgi:

```
cd hypermap/deploy
vagrant ssh
. /webapps/hypermap/bin/activate
cd /webapps/hypermap/hypermap/hypermap/
./manage.py runserver 0.0.0.0:8000
```

You can edit the files with your IDE from your host, as the directory
/webapps/hypermap/hypermap on the guest is synced with your host.

To run Celery in development mode run the worker process like this:

```
  ./manage.py celery -A hypermap worker -B -l info
```
