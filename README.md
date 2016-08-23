# HHypermap Registry

## Introduction

HHypermap (Harvard Hypermap) Registry is a platform that manages OWS, Esri REST, and other types of map service harvesting, and orchestration and maintains uptime statistics for services and layers. Where possible, layers will be cached by MapProxy. It is anticipated that other types of OGC service such as WFS, WCS, WPS, as well as flavors of Esri REST and other web-GIS protocols will eventually be included. The platform is initially being developed to collect and organize map services for Harvard WorldMap, but there is no dependency on WorldMap. HHypermap Registry publishes to HHypermap Search (based on Lucene) which provides a fast search and visualization environment for spatio-temporal materials.  The initial funding for HHypermap Registry came from a grant to the Center for Geographic Analysis from the National Endowment for the Humanities.   

## Installation

### Running Hypermap on Docker

Easiest way to have an HHypermap instance up and running is to use Docker.

```
git clone git@github.com:cga-harvard/HHypermap.git
cd HHypermap
make build
make up
make sync
make logs
```

Wait for the instance to be provisioned (about 3/4 minutes).

Then connect to: http://localhost:8000 and your instance should be up and running.


You can edit the files with your IDE from your host, as the directory
/code on the guest is synced with your host.

To run unit tests:

```
make test
```

## Start using Hypermap

Login to the home page, http://localhost:8000. It will be empty. You need to add some
endpoints to Hypermap. So go to the administrative interface:

http://localhost:8000/admin/

Go to Endpoint List and add an endpoint list, for example the one included in /data.

After saving, Hypermap should be start harvesting the endpoint.

Harvesting will be performed by the Django server if SKIP_CELERY_TASK
= True, otherwise by Celery. Please note that harvesting operations can be time consuming, so it is better to setup a Celery process if possible.
