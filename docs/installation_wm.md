# Harvard WorldMap installation

You could use GeoNode WorldMap to consume the Hypermap Registry layers in web maps.
Here is a procedure to install it in Ubuntu 16.04 LTS.

## Requirements

We are assuming a Ubuntu 16.04 LTS development environment, but these instructions can be adapted to any recent Linux distributions::

    # Install Ubuntu dependencies
    sudo apt-get update
    sudo apt-get install python-virtualenv python-dev libxml2 libxml2-dev libxslt1-dev zlib1g-dev libjpeg-dev libpq-dev libgdal-dev git default-jdk postgresql postgis

    # Install Java 8 (needed by latest GeoServer 2.14)
    sudo apt-add-repository ppa:webupd8team/java
    sudo apt-get update
    sudo apt-get install oracle-java8-installer

## Virtual environment creation and installation of Python packages

Create and activate the virtual environment::

    cd ~
    virtualenv --no-site-packages env
    . env/bin/activate

Now install GeoNode from source code::

    git clone https://github.com/geonode/geonode.git
    cd geonode
    pip install -r requirements.txt
    pip install pygdal==1.11.3.3
    pip install -e .
    paver setup

## Create the databases

```txt
sudo su postgres
psql
postgres=# CREATE ROLE worldmap WITH LOGIN SUPERUSER PASSWORD '***';
CREATE ROLE
postgres=# CREATE DATABASE worldmap WITH OWNER worldmap;
CREATE DATABASE
postgres=# \c worldmap
You are now connected to database "worldmap" as user "postgres".
worldmap=# CREATE EXTENSION postgis;
CREATE EXTENSION
worldmap=# CREATE DATABASE wmdata WITH OWNER worldmap;
CREATE DATABASE
worldmap=# \c wmdata
You are now connected to database "wmdata" as user "postgres".
wmdata=# CREATE EXTENSION postgis;
CREATE EXTENSION
```

## Environment variables setup

Set the following environment variables as needed (change SITE_NAME and SERVER_IP s needed. Also HYPERMAP_REGISTRY_URL and SOLR_URL may be different). Even better, create a file and source it::

      export USE_WORLDMAP=True
      export SITE_NAME=worldmap
      export SERVER_IP=localhost
      export PG_USERNAME=worldmap
      export PG_PASSWORD=worldmap
      export PG_WORLDMAP_DJANGO_DB=worldmap
      export PG_WORLDMAP_UPLOADS_DB=wmdata
      export OWNER=$PG_USERNAME
      export ALLOWED_HOSTS="localhost, $SERVER_IP, "
      export GEOSERVER_LOCATION=http://localhost:8080/geoserver/
      export GEOSERVER_PUBLIC_LOCATION=http://$SERVER_IP/geoserver/
      export SOLR_URL =http://localhost:8983/solr/hypermap/select/
      export HYPERMAP_REGISTRY_URL =http://localhost:8001
      export MAPPROXY_URL=http://localhost:8001


You can install GeoNode WorldMap in two different ways:

1) By installing GeoNode itself
2) By using the recommended way of a geonode-project

## GeoNode/WorldMap without a geonode-project

Copy the included local_settings.py file and customize it to your needs::

    cp local_settings.py.worldmap.sample local_settings.py

## GeoNode/WorldMap with a geonode-project

You will use a geonode-project in order to separate the customization of your instance from GeoNode.

Create your geonode project by using the WorldMap geonode-project as a template  (https://github.com/cga-harvard/geonode-project). Rename it to something meaningful (for example your web site name)::

    cd ~
    django-admin startproject $SITE_NAME --template=https://github.com/cga-harvard/geonode-project/archive/master.zip -epy,rst
    cd $SITE_NAME

Create a local_settings.py by copying the included template::

    cp $SITE_NAME/local_settings.py.sample $SITE_NAME/local_settings.py
    make build
    paver setup

## Start the Server

Start GeoNode with Worldmap using pavement::

    python manage.py runserver 0.0.0.0:8000
    paver start_geoserver

To upload layers you can login with the default GeoNode administrative account:

user: admin
password: admin

## Configuring instance for production

### uwsgi

Create a worlmap.ini script for running uwsgi. For example create it like this in /home/ubuntu:

```sh
[uwsgi]
plugins = python
processes = 4
master = true
http-socket = 0.0.0.0:8000
chmod-socket = 664
buffer-size = 32768
log-date = true
logto = /tmp/%n.log
chdir = /home/ubuntu/worldmap
module= worldmap_site.wsgi
enable-threads = true
workers = 10
virtualenv = /home/ubuntu/env
vacuum = true
socket = /tmp/worldmap.sock
max-requests = 5000 # respawn processes after serving 5000 requests
limit-as = 1024 # avoid Errno 12 cannot allocate memory

## Env Variables
env = USE_WORLDMAP=True
env = SITE_NAME=worldmap
env = SERVER_IP=your-ip
env = SITEURL=your-ip
env = PG_HOST=localhost
env = PG_USERNAME=worldmap
env = PG_PASSWORD=***
env = PG_WORLDMAP_DJANGO_DB=worldmap
env = PG_WORLDMAP_UPLOADS_DB=wmdata
#env = GEOFENCE_URL=postgresql://worldmap:***@localhost:5432/geofence
env = DEFAULT_BACKEND_DATASTORE=datastore
env = ALLOWED_HOSTS=['localhost', 'your-ip', ]
env = GEOSERVER_LOCATION=http://your-ip:8080/geoserver/
env = GEOSERVER_PUBLIC_LOCATION=http://your-ip/geoserver/
env = GEOSERVER_ADMIN_PASSWORD=geoserver
env = SOLR_URL=http://hypermap-ip:8983/solr/hypermap/select/
env = USE_HYPERMAP=True
env = HYPERMAP_REGISTRY_URL=http://hypermap-ip/
env = MAPPROXY_URL=http://hypermap-ip/
env = GOOGLE_API_KEY=***
env = DEFAULT_BACKEND_UPLOADER=geonode.importer
env = GEONAMES_USER=***
```

Test the .ini file (browse to your-ip:8000 to see if it works correctly):



Create a service script in /etc/systemd/system/worldmap.service like this:

```sh
[Unit]
Description=uWSGI instance to serve GeoNode WorldMap
After=network.target

[Service]
User=ubuntu
Group=www-data
ExecStart=/usr/bin/uwsgi --ini /home/ubuntu/worldmap.ini

[Install]
WantedBy=multi-user.target
```

Now start the uwsgi process:

```sh
sudo service worldmap start
```

To automatically start the process at server boot:

```sh
sudo systemctl enable worldmap.service
```

### nginx

If still not installed, install nginx:

```sh
sudo apt install nginx
```

Disable the default site (by removing the symbolic link in sites-enabled) and create a site for GeoNode by creating the following file in /etc/nginx/sites-available/geonode:

```sh
server {
    listen 80;
    index index.html index.htm;
    root   /usr/share/nginx/html;
    server_name your-ip;

    location /uploaded {
      alias /home/ubuntu/worldmap/worldmap_site/uploaded/;
      expires 30;
    }

    location /geoserver {
      proxy_pass http://localhost:8080/geoserver;
      proxy_redirect     off;
      proxy_set_header   Host $host;
      proxy_set_header   X-Real-IP $remote_addr;
      client_max_body_size 100M;
      proxy_read_timeout 30000;
    }

    location /solr {
      proxy_pass http://hh.worldmap.h-gis.jp:8983;
      proxy_redirect     off;
      proxy_set_header   Host $host;
      proxy_set_header   X-Real-IP $remote_addr;
      client_max_body_size 100M;
      proxy_read_timeout 30000;
    }

    location / {
    root /home/ubuntu/ritsumei;
    proxy_pass http://0.0.0.0:8000/;
    add_header Access-Control-Allow-Origin "*";

    if ($request_method = OPTIONS) {
      add_header Access-Control-Allow-Methods "GET, POST, PUT, PATCH, OPTIONS";
      add_header Access-Control-Allow-Headers "Authorization, Content-Type, Accept";
      add_header Access-Control-Allow-Credentials true;
      add_header Content-Length 0;
      add_header Content-Type text/plain;
      add_header Access-Control-Max-Age 1728000;
      return 200;
    }
    client_max_body_size 100M;
    client_body_buffer_size 128K;
    add_header Access-Control-Allow-Credentials false;
    add_header Access-Control-Allow-Headers "Content-Type, Accept, Authorization, Origin, User-Agent";
    add_header Access-Control-Allow-Methods "GET, POST, PUT, PATCH, OPTIONS";
    proxy_set_header X-Forwarded-Protocol $scheme;
    proxy_read_timeout 30000;
    proxy_redirect     off;
    proxy_set_header   Host $host;
    proxy_set_header   X-Real-IP $remote_addr;
    proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Host $server_name;
  }
}
```

Enable the site by creating a symbolic link in sites-enabled and restart nginx.

### Tomcat

```sh
cd /opt
sudo wget http://mirrors.koehn.com/apache/tomcat/tomcat-8/v8.5.37/bin/apache-tomcat-8.5.37.tar.gz
sudo tar -xvzf apache-tomcat-8.5.37.tar.gz
sudo mv apache-tomcat-8.5.37 tomcat
sudo chown -R ubuntu:ubuntu tomcat
```

Create a service script in /etc/systemd/system/tomcat.service (modify parameter as per your needs):

```
[Unit]
Description=Tomcat
After=network.target

[Service]
Type=forking

Environment=CATALINA_PID=/opt/tomcat/tomcat.pid
Environment=JAVA_HOME=/usr/lib/jvm/java-8-oracle/
Environment=CATALINA_HOME=/opt/tomcat
Environment=CATALINA_BASE=/opt/tomcat
Environment='CATALINA_OPTS=-Xmx4800m -Xms3000m -server
Environment='JAVA_OPTS=-Xmx4096m -Xms3000m -XX:MaxPermSize=4096m -XX:+UseConcMarkSweepGC -XX:+UseParNewGC -XX:ParallelGCThreads=4 -DGEOSERVER_DATA_DIR=/home/ubuntu/gs_data -DGEOWEBCACHE_CACHE_DIR=/home/ubuntu/gs_data/gwc -Djava.library.path=/usr/local/lib/ -DGEOMETRY_COLLECT_MAX_COORDINATES=50000 -Djavax.servlet.request.encoding=UTF-8 -Djavax.servlet.response.encoding=UTF-8 -Dfile.encoding=UTF-8 -Duser.timezone=GMT -Dorg.geotools.shapefile.shapefile.datetime=true -Dgeofence.dir=/home/ubuntu/gs_data/geofence -Djava.security.egd=file:/dev/./urandom'

ExecStart=/opt/tomcat/bin/startup.sh
ExecStop=/opt/tomcat/bin/shutdown.sh

User=ubuntu
Group=ubuntu

[Install]
WantedBy=multi-user.target
```

Deploy the .war to Tomcat webapps and then start the Tomcat service:

```sh
cp ~/geonode/downloaded/geoserver-2.14.x.war /opt/tomcat/webapps/
mv /opt/tomcat/webapps/geoserver-2.14.x.war /opt/tomcat/webapps/geoserver.war
sudo service tomcat start
```

Now start the Tomcat service and check if GeoServer is up and running.

To automatically start the process at server boot:

```sh
sudo systemctl enable tomcat.service
```

Hypermap Registry
=================

GeoNode with the WorldMap contribute module requires a Hypermap Registry (Hypermap) running instance.

You can install Hypermap by following these instructions (use the "Manual Installation" section): https://github.com/cga-harvard/HHypermap/blob/master/_docs/developers.md

Note that you can bypass Java 8 installation as it was installed previously. As a search engine you should install Solr, as we haven't tested Elasticsearch with WorldMap so far. Create a specific virtual environment for Hypermap in order not to interfere with the GeoNode/WorldMap virtual environment.

After installing Hypermap, start it on a different port than 8000, for example::

    python manage.py runserver 0.0.0.0:8001

In another shell start the Celery process as well::

    cd HHypermap
    celery -A hypermap worker --beat --scheduler django -l info

Test the stack
==============

Now that GeoNode/WorldMap and Hypermap are both running, test the stack by uploading a layer.

Login in GeoNode (admin/admin) and upload a shapefile from this page: http://localhost:8000/layers/upload

Make sure the shapefile is correctly displayed in GeoNode by going to the layer page.

Now login in Hypermap (admin/admin) and go to the admin services page: http://localhost:8001/admin/aggregator/service/ Add a service like this:

    * Title: My GeoNode WorldMap SDI
    * Url: http://localhost:8000/
    * Type: GeoNode WorldMap

Go to the Hypermap service page and check it the service and the layer is there:
http://localhost:8001/registry/

In order to have layers in the search engine (Solr) there are two options:

1) from task runner press the "Index cached layers" button
2) schedule a task in celery

We recommend the second option, which can be configured in the next section.

Schedule Celery tasks
=====================

Go to the Periodic Task administrative interface: http://localhost:8001/admin/django_celery_beat/periodictask/

Create the following two tasks:

Index Cached Layer Task
-----------------------

This task will sync the layers from the cache to the search engine. Layers are sent in the cache every time they are saved:

    * Name: Index Cached Layer
    * Task (registered): hypermap.aggregator.tasks.index_cached_layers
    * Interval: every 1 minute (or as needed)

Check Worldmap Service
----------------------

This task will do a check of all of WorldMap service:

    * Name: Check WorldMap Service
    * Task (registered): hypermap.aggregator.tasks.check_service
    * Interval: every 1 minute (or as needed)
    * Arguments: [1] # 1 is the id of the service. Change it as is needed

Now upload a new layer in GeoNode/WorldMap and check if it appears in Hypermap and in Solr (you may need to wait for the tasks to be executed)

Update Last GeoNode WorldMap Layers
-----------------------------------

If your GeoNode/WorldMap instance has many layers, it is preferable to runt the check_service not so often, as it can be time consuming, and rather use the update_last_wm_layers.

As a first thing, change the interval for the check_service task you created for GeoNode/WorldMap to a value such as "one day" or "one week".

Then create the following periodic task:

    * Name: Sync last layers in WorldMap Service
    * Task (registered): hypermap.aggregator.update_last_wm_layers
    * Interval: every 1 minute
    * Arguments: [1] # 1 is the id of the service. Change it as is needed
