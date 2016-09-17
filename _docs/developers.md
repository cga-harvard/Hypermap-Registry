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

*Unit tests* asserts the correct functionality of Hypermap workflow where an added endpoint, creates Services and their Layers, checks
 the correct metadata is being harvested and stored in DB and indexed in the Search backend.

```sh
make test-unit
```

*Solr backend* asserts the correct functionality of Solr implementation to index Layers with Solr and tests the Hypermap search API connected to that implementation by
querying data by the most important fields.

1. inserts 4 layers
2. test all match docs, q.text, q.geo, q.time and some facets, see the search API documentation. (#TODO link to the api docs). 

```sh
make test-solr
```

*Elasticsearch backend* asserts the correct functionality of Elasticsearch implementation to index Layers with ES and tests the Hypermap search API connected to that implementation by
querying data by the most important fields.

1. inserts 4 layers
2. test all match docs, q.text, q.geo, q.time and some facets, see the search API documentation. (#TODO link to the api docs). 

```sh
make test-elastic
```

*Selenium Browser* is an end-to-end tests that runs a Firefox and emulates the user interaction with some basic actions to test the correct funcionality of
 the Django admin site and registry UI, this test covers the following actions:
 
 1. admin login (user sessions works as expected)
 2. periodic tasks verifications (automatic periodic tasks are created on startup in order to perform important automatic tasks like check layers, index cached layers on search backend and clean up tasks)
 3. upload endpoint list (file uploads correctly and store in db, it triggers all harvesting load like: create endpoints, create services and their layers, index layers in search backend and perform firsts service checks)
 4. verify creation of endpoint, service and layers (previous workflow executed correctly)
 5. browser the search backend url (should appear indexed layers previouly created)
 6. browser /registry/ (services created are being display to users correctly)
 7. browser service details (check basic service metadata present on the page)
 8. reset service checks (correct functionality should start new check tasks)
 9. create new service checks and verification (trigger the verification tasks and verifies it in service listing page)
 10. browser layers details (check basic service metadata present on the page)
 11. reset layer checks (correct functionality should start new check tasks)
 12. create new layer checks and verification (trigger the verification tasks and verifies it in service layers listing page)
 13. clear index (tests the clean up indice functionality)
 

```sh
make test-endtoend-selenium-firefox
```

Selenium and Firefox interaction can be viewed by connecting to VNC protocol, the easiest method is to use Safari. 
Just open up Safari and in the URL bar type `vnc://localhost:5900` hit enter and entry `secret` in the password field. Other method is using VNCViever: https://www.realvnc.com/download/viewer/

*CSW-T* asserts the correct functionality of CSW transaction requests. 

1. inserts a full XML documents with `request=Transaction` and verifies Layers created correctly, the inserted document with 10 Layers can be found here: `data/cswt_insert.xml`
2. verifies the Listing by calling  `request=GetRecords` and asserting 10 Layers created.
3. verifies the search by calling `request=GetRecords` and passing a `q` parameter.
4. as that harvesting method also sends the layers to the search backend, a verification is made in order to assert the 10 layers created.

```sh
make - test-csw-transactions
```

To run all tests above in a single command:

```sh
make test
```

##### Travis Continuos Integration Server

`master` branch is automaticaly synced on https://travis-ci.org/ and reporting test results, too see how travis is running tests refer to the `.travis.yml` file placed in the project root.
If you want to run tests in your local containers first, Execute travis-solo (`pip install travis-solo`) in directory containing .travis.yml configuration file. It’s return code will be 0 in case of success and non-zero in case of failure.

##### Tool For Style Guide Enforcement

The modular source code checker for `pep8`, `pyflakes` and `co` runs thanks to `flake8` already installed with the project requirements and can be executed with this command:

```sh
make flake
```

Note that Travis-CI will assert flake returns 0 code incidences.

## Known Issues in version 0.3.9

 - Items from Brazil appear in Australia: https://github.com/cga-harvard/HHypermap/issues/199
 - Service name is not set up properly when ingesting via CSW-T: https://github.com/cga-harvard/HHypermap/issues/200
 - Some bounding boxes are advertised as EPSG:4326 but have values in an invalid range: https://github.com/cga-harvard/HHypermap/issues/192
 - Service and Layer checks can cause overload on remote servers. Checks should not be so exhaustive. https://github.com/cga-harvard/HHypermap/issues/173
 - Last check date is not being reported, last modification date is being reported instead. https://github.com/cga-harvard/HHypermap/issues/201
 - Sibling services are being imported in ArcGIS services: https://github.com/cga-harvard/HHypermap/issues/203


## Changelog
Master

 - Removed dependency on pylibmc. Fixes #181.

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
