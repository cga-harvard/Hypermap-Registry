# Installation

You can have a development working setup using one of the following methods:

* Manual Installation (last tested: 11/17/2017)
* Docker Installation (last tested: June 2017)

Please provide feedback opening a ticket if these instructions are failing.

## Manual Installation

We will assume you are installing every Hypermap Registry component (web application, search engine, RDBMS and task queue) on a single server, but they can be installed on different servers as well.

### Requirements

We are assuming a Ubuntu 16.04.1 LTS development environment, but these instructions can be adapted to any recent Linux distributions.

Install the requirements:

```sh
sudo apt-get update
sudo apt-get install gcc postgresql rabbitmq-server python-virtualenv git python-psycopg2 libjpeg-dev python-dev libxml2-dev libxslt-dev libxslt1-dev libpq-dev libgeos-dev memcached libmemcached-dev
```

### RDBMS

As the database, we recommend to use PostgreSQL, but any RDBMS supported by Django can be used.

Create PostgreSQL database:

```sh
sudo -i -u postgres
psql
CREATE ROLE hypermap WITH SUPERUSER LOGIN PASSWORD 'hypermap';
CREATE DATABASE hypermap WITH OWNER hypermap;
postgres=# \q
```

### Search Engine

Now you need to install a search engine, which can be Solr or Elasticsearch. Both of them require Java.

Install java8:
```sh
sudo add-apt-repository ppa:webupd8team/java
sudo apt-get update
sudo apt-get install oracle-java8-installer
```

Now follow the instrcutions for Solr or Elasticsearch, depending on your scenario.

#### Solr (Recommended)

Install and start Solr, and create the hypermap schema:

```sh
cd /opt
sudo wget http://archive.apache.org/dist/lucene/solr/6.6.2/solr-6.6.2.tgz
sudo tar xzf solr-7.3.0.tgz solr-7.3.0/bin/install_solr_service.sh --strip-components=2
sudo ./install_solr_service.sh solr-7.3.0.tgz
sudo -u solr solr/bin/solr create -c hypermap
sudo -u solr solr/bin/solr config -c hypermap -p 8983 -property update.autoCreateFields -value false
```

#### Elasticsearch

Install and start Elasticsearch:

```sh
wget -qO - https://packages.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
echo "deb https://packages.elastic.co/elasticsearch/2.x/debian stable main" | sudo tee -a /etc/apt/sources.list.d/elasticsearch-2.x.list
sudo apt-get update && sudo apt-get install elasticsearch
sudo sed -i -e 's/#ES_HEAP_SIZE=2g/ES_HEAP_SIZE=1g/' /etc/default/elasticsearch
sudo service elasticsearch start
```

TODO explain how to create a schema in Elasticsearch.

#### Web Application

Install Hypermap, which is a web application based on Django, using a virtual environment.

```sh
cd ~
virtualenv --no-site-packages env
source env/bin/activate
git clone https://github.com/cga-harvard/Hypermap-Registry.git
cd Hypermap-Registry
pip install -r requirements.txt
```

To set the environment variables, create an env_vars and copy and paste the lines below to the end (change the lines according to your configuration)

```sh
export DATABASE_URL=postgres://hypermap:hypermap@localhost:5432/hypermap
export BROKER_URL=amqp://guest:guest@localhost:5672/
export CACHE_URL=memcached://localhost:11211/
export BASE_URL=http://localhost
export ALLOWED_HOSTS=['localhost',]
export REGISTRY_SEARCH_URL=solr+http://localhost:8983
export REGISTRY_CHECK_PERIOD=120
export REGISTRY_SKIP_CELERY=False
export REGISTRY_LIMIT_LAYERS=0
export REGISTRY_INDEX_CACHED_LAYERS_PERIOD=1
export REGISTRY_HARVEST_SERVICES=True
export C_FORCE_ROOT=1
export CELERY_DEFAULT_EXCHANGE=hypermap
```

Source the env_vars file

```
source env_vars
```

Execute migrations, which will generate the schema in the database:

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
python manage.py runserver 0.0.0.0:8000
```

Using another shell, start the Celery process after activating the virtualenv:

```
cd HHypermap
celery -A hypermap worker --beat --scheduler django -l info
```

Now if you browse to http://localhost:8000, Hypermap should be up and running.

## Docker Installation

You can have an Hypermap Registry instance up and running using Docker.

Install Docker and Docker Compose:

```
wget https://get.docker.com/builds/Linux/x86_64/docker-latest.tgz
tar -xvzf docker-latest.tgz
sudo mv docker/* /usr/bin/
curl -L https://github.com/docker/compose/releases/download/1.8.0/docker-compose-`uname -s`-`uname -m` > docker-compose
chmod +x docker-compose
sudo mv docker-compose /usr/bin/
sudo usermod -aG docker $(whoami)
```

### Increase virtual memory map area (Linux)

```
sudo sysctl -w vm.max_map_count=262144
```

### Run docker in daemon

```sh
sudo dockerd
```

### Deployment of hhypermap within docker

```sh
git clone https://github.com/cga-harvard/Hypermap-Registry.git
cd Hypermap-Registry
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

## Running Hypermap in production

When running Hypermap in production it is highly recommended to use a proper web sever (nginx or Apache httpd) in place of the Django server.

You can find a sample configuration for nginx and uwsgi in the config directory (nginx_sample and uwsgi_sample files).

In case you want to automate this, there are ansible script for the deployment in the deploy/ansible directory (which need to be updated).

## For developers

### Testing Hypermap Registry

If you want to provide pull requests to Hypermap-Registry, you should make sure that your changes don't break tests before submitting the pull request.

*Unit tests* check the correct functionality of Hypermap workflow when an endpoint is added: some services and their layers are created, then the tests check
 if the correct metadata are harvested and stored in DB and indexed in the search backend.

 To run the unit tests:

```sh
make test-unit
```

*Solr backend tests* check that the Solr search engine implementation works correctly: tests index layers in Solr and test the Hypermap search API is working properly.

```sh
make test-solr
```

*Elasticsearch backend tests* check that the Elasticsearch search engine implementation works correctly: tests index layers in Elasticsearch and test the Hypermap search API is working properly.

```sh
make test-elastic
```

*Selenium Browser tests* emulate the user interaction in Firefox with some basic actions to test the correct functionality of the Django admin site and registry UI. Tests cover the following actions:

 1. admin login (user sessions works as expected)
 2. periodic tasks verifications (automatic periodic tasks are created on startup in order to perform important automatic tasks like check layers, index cached layers on search backend and clean up tasks)
 3. upload endpoint list (file with endpoint list is correctly uploaded and stored in the database, and triggers all harvesting actions like: create endpoints, create services and their layers, index layers in search backend and firsts service checks)
 4. verify creation of endpoint, service and layers
 5. check if the layers created in test are in the search backend url
 6. browser /registry/ (services created are being display to users correctly)
 7. browser service details (check basic service metadata present on the page)
 8. reset service checks (correct functionality should start new check tasks)
 9. create new service checks and verification (trigger the verification tasks and verifies it in service listing page)
 10. browser layers details (check basic service metadata present on the page)
 11. reset layer checks (correct functionality should start new check tasks)
 12. create new layer checks and verification (trigger the verification tasks and verifies it in service layers listing page)
 13. clear index (tests the clean up indice functionality)

To run these tests:

```sh
make test-endtoend-selenium-firefox
```

Selenium and Firefox interaction can be viewed by connecting to VNC protocol, the easiest method is to use Safari.

Just open up Safari and in the URL bar type `vnc://localhost:5900` hit enter and entry `secret` in the password field. Other method is using VNCViever: https://www.realvnc.com/download/viewer/

*CSW-T tests* check the correct functionality of CSW transaction requests.

1. inserts a full XML documents with `request=Transaction` and verifies layers are created correctly. This test use a fixture which can be found here: `data/cswt_insert.xml`
2. verifies the listing by calling  `request=GetRecords` and asserting 10 Layers created.
3. verifies the search by calling `request=GetRecords` and passing a `q` parameter.
4. as that harvesting method also sends the layers to the search backend, a verification is made in order to assert the 10 layers created.

```sh
make - test-csw-transactions
```

To run all tests above in a single command:

```sh
make test
```

#### Style guide enforcement

The modular source code checker for `pep8`, `pyflakes` and `co` runs thanks to `flake8` already installed with the project requirements and can be executed with this command:

```sh
make flake
```

#### Continuos integration

`master` branch is automatically built on https://travis-ci.org/ Travis can be configured in the `.travis.yml` file placed in the project root.

If you want to run tests in your local containers first, execute travis-solo (`pip install travis-solo`) in directory containing .travis.yml configuration file. It’s return code will be 0 in case of success and non-zero in case of failure.

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
