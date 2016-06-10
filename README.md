# HHypermap Supervisor

## Introduction

HHypermap (Harvard Hypermap) Supervisor is a platform that manages OWS, Esri REST, and other types of map service harvesting, and orchestration and maintains uptime statistics for services and layers. Where possible, layers will be cached by MapProxy. It is anticipated that other types of OGC service such as WFS, WCS, WPS, as well as flavors of Esri REST and other web-GIS protocols will eventually be included. The platform is initially being developed to collect and organize map services for Harvard WorldMap, but there is no dependency on WorldMap. HHypermap Supervisor publishes to HHypermap Search (based on Lucene) which provides a fast search and visualization environment for spatio-temporal materials.  The initial funding for HHypermap Supervisor came from a grant to the Center for Geographic Analysis from the National Endowment for the Humanities.   

## Installation

### Running Hypermap on Vagrant

Easiest way to have an HHypermap instance up and running is to use Vagrant.

```
git clone git@github.com:cga-harvard/hypermap.git
cd hypermap/deploy
vagrant up
```

Wait for the instance to be provisioned (about 3/4 minutes).

Then connect to: 192.168.33.15 and your instance should be up and running.


#### Development mode on Vagrant

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

To run Celery in development mode run the worker process like this (remember to stop the celery process with supervisor before):

```
./manage.py celery -A hypermap worker -B -l info
```

To run unit tests:

```
cd /webapps/hypermap/hypermap
paver run_tests
```

If you want to run integration tests, you need to create a solr core named 'hypermap_test', and then:

```
cd /webapps/hypermap/hypermap
paver run_integration_tests
```

### Running Hypermap on AWS

Make sure to have the following variables correctly set:

```
bash-3.2$ echo $ANSIBLE_HOSTS
/Users/capooti/ec2.py
bash-3.2$ echo $EC2_INI_PATH
/Users/capooti/ec2.ini
bash-3.2$ echo $AWS_ACCESS_KEY_ID
AKI...
bash-3.2$ echo $AWS_SECRET_ACCESS_KEY
djE...
```

Also, set the ssh-agent and make sure it is running correctly:

```
ssh-agent bash
bash-3.2$ ssh-add ~/.ssh/cga.pem
bash-3.2$ ssh-add -L
ssh-rsa AAAAB3NzaC1yc2E... /Users/capooti/.ssh/cga.pem
```

Finally run the playbook:

ansible-playbook aws.yml

If you want to run only a part of the provisioning process use the --tags option:

ansible-playbook aws.yml --tags "uwsgi"

To make a new deployment, after committing to git, run:

ansible-playbook deploy.yml


### Manual Installation

We will assume that you are installing Hypermap on Ubuntu 14.04 LTS.

First, install requirements:

```
sudo apt-get update
sudo apt-get install python-dev postgresql postgresql-server-dev-all
libjpeg-dev rabbitmq-server
```

Create PostgreSQL role and database:

```
sudo su postgres
psql
CREATE USER hypermap WITH superuser PASSWORD 'hypermap';
CREATE DATABASE hypermap WITH OWNER hypermap;
```

Install Hypermap on a virtual environment:

```
virtualenv --no-site-packages env
source env/bin/activate
pip install --upgrade pip
git clone https://github.com/cga-harvard/HHypermap.git
pip install -e HHypermap
```

You need to create a settings file named as your username:

```
cd HHypermap/hypermap
touch settings/_yourusername.py
```

In _yourusername.py you need to add at least the first line, and then the settings specific for your environment, such as preferences about Celery and Solr:

```
from settings.default import *  # noqa

SITE_URL = 'http://localhost:8000/'

SEARCH_ENABLED = True
SEARCH_TYPE = 'solr'
SEARCH_URL = 'http://127.0.0.1:8983/solr/search'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'hypermap',
        'USER': 'hypermap',
        'PASSWORD': 'hypermap',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

SKIP_CELERY_TASK = True
```

Now synchronize the database:

./manage.py syncdb # create an admin user when requested

Now you should be able to start the development server:

./manage.py runserver


## Start using Hypermap

Login to the home page, http://localhost:8000. It will be empty. You need to add some
endpoints to Hypermap. So go to the administrative interface:

http://localhost:8000/admin/

Go to Service and add a service of WMS type. As a endpoint you can use this one:
http://demo.geonode.org/geoserver/ows?service=wms&version=1.1.1&request=GetCapabilities

After saving, Hypermap should be start harvesting the endpoint.

Harvesting will be performed by the Django server if SKIP_CELERY_TASK
= True, otherwise by Celery. Please note that harvesting operations can be time consuming, so it is better to setup a Celery process if possible.
