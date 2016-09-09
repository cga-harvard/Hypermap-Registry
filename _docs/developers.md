# HHypermap for developers

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
export DATABASE_URL=hypermap://hypermap:postgres@postgres:5432/hypermap
export BROKER_URL=amqp://guest:guest@rabbitmq:5672/
export CACHE_URL=memcached://memcached:11211/
export BASE_URL=django
export ALLOWED_HOSTS=['django',]
export REGISTRY_SEARCH_URL=elasticsearch+http://elasticsearch:9200/
export REGISTRY_MAPPING_PRECISION=500m
export REGISTRY_CHECK_PERIOD=120
export REGISTRY_SKIP_CELERY=False
export REGISTRY_LIMIT_LAYERS=0
export REGISTRY_INDEX_CACHED_LAYERS_PERIOD=1
export REGISTRY_HARVEST_SERVICES=True
export C_FORCE_ROOT=1
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
make up
make sync
```
Wait for the instance to be provisioned (about 3/4 minutes).

Then connect to: http://localhost/registry and your instance should be up and running.

You can edit the files with your IDE from your host, as the directory /code on the guest is synced with your host. Make sure to check the ```REGISTRY_SKIP_CELERY``` environment variable is set to False for debugging. If this value is set to False, it is always necessary to restart the celery container executing

```sh
docker-compose restart celery
```

##### Tests commands

Unit tests

```sh
make test-unit
```

Solr backend

```sh
make test-solr
```

Elasticsearch backend

```sh
make test-elastic
```

Selenium

```sh
make test-endtoend-selenium-firefox
```

To run all tests above in a single command:

```sh
make test
```

## Known Issues in version 0.3.9

 - Items from Brazil appear in Australia: https://github.com/cga-harvard/HHypermap/issues/199
 - Service name is not set up properly when ingesting via CSW-T: https://github.com/cga-harvard/HHypermap/issues/200
 - Some bounding boxes are advertised as EPSG:4326 but have values in an invalid range: https://github.com/cga-harvard/HHypermap/issues/192
 - Service and Layer checks can cause overload on remote servers. Checks should not be so exhaustive. https://github.com/cga-harvard/HHypermap/issues/173
 - Last check date is not being reported, last modification date is being reported instead. https://github.com/cga-harvard/HHypermap/issues/201
 - Sibling services are being imported in ArcGIS services: https://github.com/cga-harvard/HHypermap/issues/203


## Changelog
Version 0.3.11

 - Move to Elasticsearch 1.7 compatible query syntax.

Version 0.3.10

 - CSW-T Insert support with custom <registry> tags.
 - Custom <registry> tags available in MapLoom UI.
 - Full screen MapLoom Registry modal.
 - Adaptive pagination based on available height.
 - Fixed MapProxy issues with WMS servers. workspace:name is now sent as layer name instead of name.
 - Fixed map display issues on hover for ArcGIS layers.
 - is_monitored is set to False on services uploaded via CSW-T.
 - Added users, admins and developers documentation.
 - More robust parsing of ArcGIS services url.
 - Switched to q.param and a.param instead of a_param and q_param for future compatibility with angular-search.
 - Added uuid field, requires migrations.

Version 0.3

 - Swagger API support. Deprecated CATALOGLIST.
 - Multi Catalog.
 - Docker for development.
 - Standalone third party app.

Version 0.2

 - Elasticsearch support.
 - MapLoom UI.
 - ArcGIS MapServer support.
