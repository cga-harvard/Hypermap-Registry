# HHypermap for developers

## Installation

You can have a development working setup using one of the following methods:

* Manual Installation (last tested: 11/17/2017)
* Docker Installation (last tested: June 2017)

Please provide feedback opening a ticket if these instructions are failing.

### Manual Installation

We will assume you are installing every Hypermap component (web application, search engine, RDBMS and task queue) on a single server, but they can be installed on different servers as well.

#### Requirements

Install the requirements:

```sh
sudo apt-get update
sudo apt-get install gcc postgresql rabbitmq-server python-virtualenv git python-psycopg2 libjpeg-dev python-dev libxml2-dev libxslt-dev libxslt1-dev libpq-dev libgeos-dev memcached libmemcached-dev
```

#### RDBMS

Create PostgreSQL database.

```sh
CREATE ROLE hypermap WITH SUPERUSER LOGIN PASSWORD 'hypermap';
CREATE DATABASE hypermap WITH OWNER hypermap;
postgres=# \q
```

#### Search Engine

Install java8:
```sh
sudo add-apt-repository ppa:webupd8team/java
sudo apt-get update
sudo apt-get install oracle-java8-installer
```
Now depending if you use Elasticsearch follow the search engine installation instructions:

##### Solr

Install and start Solr, and create the hypermap schema:

```sh
cd /opt
sudo wget http://archive.apache.org/dist/lucene/solr/6.6.2/solr-6.6.2.tgz
sudo tar xzf solr-6.6.2.tgz solr-6.6.2/bin/install_solr_service.sh --strip-components=2
sudo ./install_solr_service.sh solr-6.6.2.tgz
sudo -u solr ./bin/solr create -c hypermap
```

##### Elasticsearch

Install and start Elasticsearch:

```sh
wget -qO - https://packages.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
echo "deb https://packages.elastic.co/elasticsearch/2.x/debian stable main" | sudo tee -a /etc/apt/sources.list.d/elasticsearch-2.x.list
sudo apt-get update && sudo apt-get install elasticsearch
sudo sed -i -e 's/#ES_HEAP_SIZE=2g/ES_HEAP_SIZE=1g/' /etc/default/elasticsearch
sudo service elasticsearch start
```

#### Web Application

Install Hypermap on a virtual environment.

```sh
cd ~
virtualenv --no-site-packages env
source env/bin/activate
git clone https://github.com/cga-harvard/HHypermap.git
cd HHypermap
pip install -r requirements
```

Create environment variables:

Open /env/bin/activate in a text edit and copy and paste the lines below to the end (change the lines according to your configuration):

```sh
export DATABASE_URL=postgres://hypermap:hypermap@localhost:5432/hypermap
export BROKER_URL=amqp://guest:guest@localhost:5672/
export CACHE_URL=memcached://localhost:11211/
export BASE_URL=http://localhost
export ALLOWED_HOSTS=['localhost',]
export REGISTRY_SEARCH_URL=solr+http://localhost:8983
export REGISTRY_MAPPING_PRECISION=500m
export REGISTRY_CHECK_PERIOD=120
export REGISTRY_SKIP_CELERY=False
export REGISTRY_LIMIT_LAYERS=0
export REGISTRY_INDEX_CACHED_LAYERS_PERIOD=1
export REGISTRY_HARVEST_SERVICES=True
export C_FORCE_ROOT=1
export CELERY_DEFAULT_EXCHANGE=hypermap
```

Activate again the virtualenv:

```
source env/bin/activate
```

Execute migrations

```sh
python manage.py migrate
```

Finally, load fixtures
```sh
python manage.py loaddata hypermap/aggregator/fixtures/catalog_default.json
python manage.py loaddata hypermap/aggregator/fixtures/user.json
```

If using Solr, update the schema:

```sh
python manage.py solr_scheme
```

Run the Django server:

```
python manage.py runserver
```

Using another shell, start the Celery process after activating the virtualenv:

```
celery -A hypermap worker --beat --scheduler django -l info
```

Now if you browse to http://localhost:8000, Hypermap should be up and running.

### Docker Installation

Easiest way to have an HHypermap instance up and running is to use Docker.

```
wget https://get.docker.com/builds/Linux/x86_64/docker-latest.tgz
tar -xvzf docker-latest.tgz
sudo mv docker/* /usr/bin/
curl -L https://github.com/docker/compose/releases/download/1.8.0/docker-compose-`uname -s`-`uname -m` > docker-compose
chmod +x docker-compose
sudo mv docker-compose /usr/bin/
sudo usermod -aG docker $(whoami)
```

#### Increase virtual memory map area (Linux)

```
sudo sysctl -w vm.max_map_count=262144
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
For Ubuntu:
```
make up .
make sync
```
Wait for the instance to be provisioned (about 3/4 minutes).

Then connect to: http://localhost/registry and your instance should be up and running.

You can edit the files with your IDE from your host, as the directory /code on the guest is synced with your host. Make sure to check the ```REGISTRY_SKIP_CELERY``` environment variable is set to False for debugging. If this value is set to False, it is always necessary to restart the celery container executing

```sh
docker-compose restart celery
```

## For developers

#### Tests commands

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

### Travis Continuos Integration Server

`master` branch is automaticaly synced on https://travis-ci.org/ and reporting test results, too see how travis is running tests refer to the `.travis.yml` file placed in the project root.
If you want to run tests in your local containers first, Execute travis-solo (`pip install travis-solo`) in directory containing .travis.yml configuration file. It’s return code will be 0 in case of success and non-zero in case of failure.

#### Tool For Style Guide Enforcement

The modular source code checker for `pep8`, `pyflakes` and `co` runs thanks to `flake8` already installed with the project requirements and can be executed with this command:

```sh
make flake
```

Note that Travis-CI will assert flake returns 0 code incidences.

### Translating Hypermap

As a first step, make sure your language files are included in WorldMap. Languages file are in the hypermap/hypermap/locale directory.

If your locale file is not there, you can generate it with the Django makemessages command. For example for Italian:

```
cd ~/hypermap.git
python manage.py makemessages -l it
```

Open the locale file you want to translate, in this case hypermap/hypermap/locale/it/LC_MESSAGES/django.po, and edit the translation strings as needed, for example:

```
#: hypermap/aggregator/templates/aggregator/layer_checks.html:126
#: hypermap/aggregator/templates/aggregator/search.html:11
#: hypermap/aggregator/templates/aggregator/service_checks.html:134
msgid "seconds"
msgstr "secondi"
```

Once you have translated the strings you want, you need to compile them before you see them in the site. For this purpose you can use the Django compilemessages command:

```
python manage.py compilemessages
```

Now if you browse the site you should see your translations correctly in place.

The makemessages and compilemessages needs the GNU gettext toolset to be installed on your computer. For Ubuntu 16.04 LTS this can be done in this way:

```
sudo apt-get install gettext
```

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
