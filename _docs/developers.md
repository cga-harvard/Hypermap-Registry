# Hypermap registry

## Introduction

HHypermap (Harvard Hypermap) Registry is a platform that manages OWS, Esri REST, and other types of map service harvesting, and orchestration and maintains uptime statistics for services and layers. Where possible, layers will be cached by MapProxy. It is anticipated that other types of OGC service such as WFS, WCS, WPS, as well as flavors of Esri REST and other web-GIS protocols will eventually be included. The platform is initially being developed to collect and organize map services for Harvard WorldMap, but there is no dependency on WorldMap. HHypermap Registry publishes to HHypermap Search (based on Lucene) which provides a fast search and visualization environment for spatio-temporal materials. The initial funding for HHypermap Registry came from a grant to the Center for Geographic Analysis from the National Endowment for the Humanities.

**source:** https://github.com/cga-harvard/HHypermap/README.md

## Installation

### Manual Installation

Using ubuntu 14.04

```sh
sudo apt-get update
sudo apt-get install postgresql rabbitmq-server python-virtualenv git python-psycopg2 libjpeg-dev python-dev libxml2-dev libxslt-dev libxslt1-dev libpq-dev libgeos-dev
```

Create PostgreSQL database.

```sh
sudo -u postgres psql
CREATE DATABASE hypermap;
CREATE USER hypermap WITH superuser PASSWORD 'hypermap';
\q
```

Install java8 for elasticsearch
```sh
sudo add-apt-repository ppa:webupd8team/java
sudo apt-get update
sudo apt-get install oracle-java8-installer
```

Install and configure elasticsearch

```sh
wget -qO - https://packages.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
echo "deb https://packages.elastic.co/elasticsearch/2.x/debian stable main" | sudo tee -a /etc/apt/sources.list.d/elasticsearch-2.x.list
sudo apt-get update && sudo apt-get install elasticsearch
sudo sed -i -e 's/#ES_HEAP_SIZE=2g/ES_HEAP_SIZE=1g/' /etc/default/elasticsearch
sudo service elasticsearch start
```

Install registry on a virtual environment.

```sh
virtualenv --no-site-packages env
source env/bin/activate
git clone https://github.com/cga-harvard/HHypermap.git
cd HHypermap
git checkout registry
pip install -e .
```
Create environment variables. 

```sh
#!/bin/bash
export DJANGO_SETTINGS_MODULE=hypermap.settings
export REGISTRY_SEARCH_URL=elasticsearch+http://elasticsearch:9200/
export DATABASE_URL=postgres://postgres:postgres@postgres:5432/postgres
export BROKER_URL=amqp://guest:guest@rabbitmq:5672/
export ALLOWED_HOSTS=['django',]
export C_FORCE_ROOT=1
export SEARCH_MAPPING_PRECISION=50m
export CELERY_DEFAULT_EXCHANGE=hypermap
```

Execute migrations.

```sh
python manage.py migrate
```

Finally, load fixtures
```sh
python manage.py loaddata hypermap/aggregator/fixtures/catalog_default.json
python manage.py loaddata hypermap/aggregator/fixtures/user.json
```

### Running Hypermap on Docker

Easiest way to have an HHypermap instance up and running is to use Docker.

#### Docker installation
```
wget https://get.docker.com/builds/Linux/x86_64/docker-latest.tgz
curl -L https://github.com/docker/compose/releases/download/1.8.0/docker-compose-`uname -s`-`uname -m` > docker-compose
chmod +x docker-compose
sudo mv docker-compose /usr/bin/
sudo usermod -aG docker $(whoami)
```

#### Run docker in daemon

```sh
sudo dockerd
```

#### Deployment of hhypermap within docker

```sh
git clone https://github.com/cga-harvard/HHypermap.git
cd HHypermap
git checkout registry
make build
make up
make sync
make logs
```
Wait for the instance to be provisioned (about 3/4 minutes).

Then connect to: http://localhost:8000/registry and your instance should be up and running.

You can edit the files with your IDE from your host, as the directory /code on the guest is synced with your host.

To run unit tests:
```sh
make test
```

