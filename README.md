# HHypermap Supervisor

## Introduction

HHypermap (Harvard Hypermap) Supervisor is an application that manages OWS, Esri REST, and other types of map service harvesting, and maintains uptime statistics for services and layers. When possible, layers will be cached by MapProxy. It is anticipated that other types of service such as WFS, WCS, and WPS will eventually be included. The application will be used by Harvard WorldMap to collect and manage remote layers. HHypermap Supervisor will publish to HHypermap Search (based on Lucene) which provides a fast search and visualization environment for spatio-temporal materials.   

## Hypermap on Vagrant

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

## Hypermap on AWS

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

To make a new deployment, after committing to Git, run:

ansible-playbook deploy.yml
