# Create layers from endpoint

In HHypermap Registry it is possible to harvest map services (OGC and ESRI REST) in different ways. You can create services using a single endpoint or creating a list of endpoints. An endpoint could be defined as a server's url address of services required for harvesting.

Here is a list of some sampe endpoint for each kind of servies:

* An OGC WMS endpoint: http://demo.geonode.org/geoserver/ows
* A MapWarper endpoint: http://maps.nypl.org/warper/maps
* An OGC WMTS endpoint: http://map1.vis.earthdata.nasa.gov/wmts-geo/1.0.0/WMTSCapabilities.xml
* An ESRI MapServer endpoint: https://gis.ngdc.noaa.gov/arcgis/rest/services/SampleWorldCities/MapServer/?f=json
* An ESRI ImageServer endpoint: https://gis.ngdc.noaa.gov/arcgis/rest/services/bag_bathymetry/ImageServer/?f=json
* A WorldMap endpoint: http://worldmap.harvard.edu

All of these sample endpoints can be harvested and health checked by HHypermap Registry.

Assuming that you have HHypermap Registry installed and running in your development/production server (including fixtures), enter in your browser the url: http://your_url/registry. In case you are running Registry in a development server, the url corresponds to http://localhost:8000/registry. The request response will be the following page.

![image](https://cloud.githubusercontent.com/assets/3285923/17596743/693d5392-5fb8-11e6-9a1d-5873295f1563.png)
*Application index page*

## Accessing the administration panel.

In order to access to the administration panel, in your browser enter http://localhost:8000/admin. Access through your credentials (**user:** admin, **password:** admin). The server will respond with the administrative panel page (See figure below)

![image](https://cloud.githubusercontent.com/assets/3285923/17597227/86e11dfa-5fba-11e6-80db-a5417c42a1e2.png)
*Administrative panel*

## Harvest services from a single endpoint

HHypermap Registry is designed to create a service that contains information layers given a single endpoint url. To perform this, in the administrative panel, aggregator section, select Endpoints options. There you can check which endpoints have been added before and some other options. To add other endpoints, press the button *Add endpoint*. The following page will be shown

![image](https://cloud.githubusercontent.com/assets/3285923/17601195/8bf6fe24-5fcc-11e6-8b19-6ec08bcaa1dd.png)
*Add new endpoint page response*

![image](https://cloud.githubusercontent.com/assets/3285923/17606021/f0484be2-5fe2-11e6-930b-e29f4d959a8e.png)
*Adding a new endpoint to the database*

The required fields to add an endpoint are *url* and *catalog*. After the new endpoint is added in the database, the Celery workers start the harvesting process. Hhypermap Registry fetches layers from a service, generates thumbnails and index each layer metadata to the search backend.
![image](https://cloud.githubusercontent.com/assets/3285923/17606202/dbd00690-5fe3-11e6-866d-b97c17a2eb4a.png)

Now it is possible to check in the HHypermap Registry page the created service and layers.

![image](https://cloud.githubusercontent.com/assets/3285923/17606743/c42c4b2c-5fe6-11e6-89f3-b7a921dba0bc.png)

## Harvest services from an endpointlist

Hhypermap registry has the ability to start the harvesting process of services, giving a list of endpoints within a text file. This text file must have on each line a service endpoint. For example:

```
http://worldmap.harvard.edu/
http://warp.worldmap.harvard.edu/maps
http://geonode.state.gov/
http://kgs.uky.edu/
http://servicesig102.lehavre.fr/arcgi...
```

Now, go to the administrative panel, Endpoint list section, add endpoint list. There, it is possible to choose the file to use, select the catalog and press save. After this, the application starts harvesting layers for each service independently and adds them into the search backend.

**Note:** Arcgis services have the option to fetch information layers from multiple endpoints within a folder. HHypermap registry comes with the option to create layers from a folder, giving only one of the endpoints that belong to the respective folder. This is possible checking the **greedy** option.

## Visualization

Note: the map viewer, maploom, based on Angular is not anymore supported in HHypermap Registry since version 0.3.12.
We are willing to have a new map viewer based on React at some point.

It is possible to access to the map viewer using the http://localhost/_maploom/ url. In order to visualize the layers harvested by HHypermap Registry, is necessary to press the equal sign button next to Registry in the upper left corner of the image below.

![image](https://cloud.githubusercontent.com/assets/3285923/18094804/4f5365fc-6e9a-11e6-82fc-e0d052ca8d38.png)
*Hypermap/registry visualization of layers main page*

![image](https://cloud.githubusercontent.com/assets/7197750/17906032/c85c89da-6975-11e6-8f99-d9ccc7fd6ac6.png)
*Maploom registry Main view*

With this tool the Exchange user is able to select preview and add layers into the map (see figure below).

![zbkciztqro](https://cloud.githubusercontent.com/assets/7197750/17906534/0cc12eee-6978-11e6-8f63-a6b3e71da48d.gif)
*Select a layer, watch the preview and add to map*

HHypermap Registry visualization tool comes with different types of filtering:

### Filter by catalog:
![xktxihhlyn](https://cloud.githubusercontent.com/assets/7197750/17909781/511fbac0-6986-11e6-9c7f-3ce715003342.gif)

### Filter by text:
![hiuxr72s9g](https://cloud.githubusercontent.com/assets/7197750/17906623/6fb7f154-6978-11e6-8bf1-45dd9498c623.gif)

### Filter by time:
![pvdntyqcce](https://cloud.githubusercontent.com/assets/7197750/17907248/577ff552-697b-11e6-94ec-e432baa0b71b.gif)

### Filter by area:
![yfluybilt9](https://cloud.githubusercontent.com/assets/7197750/17907216/2297d558-697b-11e6-946b-406d209ca2c6.gif)

*Note.* In the figure presented below, the maploom registry has the ability to add multiple layers to the map in a simple way. It is just necessary to select the desired layers and press the **Add** button.

### Select multiple layers at time
![gbhkcptns5](https://cloud.githubusercontent.com/assets/7197750/17906702/b8980710-6978-11e6-87c9-cc94be81e68b.gif)

## Testing


### How to connect with Hypermap features

There are tree ways to connect with hypermap functionalities:

### 1. Registry web app

#### Creating layers

- **WMS testing:** Upload http://demo.opengeo.org/geoserver/wms. There should be 72 layers created and indexed in search backend.
- Modify environment variable REGISTRY_LIMIT_LAYERS to 2. If you are using Docker, modify your docker-compose.yml file for both django and celery docker images and verify that no service has more than 2 layers.
- Verify that the number of layers created in the database and documents indexed in search backend are the same.
- the total number when the map UI client is loaded matches the total number of records in elasticsearch and the total number of layers in registry's home page.

#### Service detail page.

- Using a previously generated service from an endpoint, remove checks using **Remove Checks** button. Then press Check now button and verify in the celery monitor tab that check task is run. After the check is finished  you can verify the number of total checks in the *monitoring period* section.
![image](https://cloud.githubusercontent.com/assets/3285923/17679102/91ec62b6-62ff-11e6-8672-4dfe306c7aa6.png)

![image](http://d.pr/i/16v0E+)

#### Celery monitor and search backend indexing

- Using a previously created service. Verify that all layers are indexed in search backend. For elasticsearch you can verify executing this commmand in terminal.
```sh
    curl http://localhost:9200/_cat/indices?v
```
- To remove documents in the search backend, press *clear index* button. And verify that there are not document indexed in the given index.
- Press *Reindex all layers* to add all created layers into the search backend. And verify in the search backend.
![image](https://cloud.githubusercontent.com/assets/3285923/17679268/584b7faa-6300-11e6-9bf3-31007ca6ce8f.png)
![image](http://d.pr/i/P0I1+)

### 2. Search API

This document outlines the architecture and specifications of the HHypermap Search API.

#### API Documentation powered by Swagger

The goal of Swagger is to define a standard, language-agnostic interface to REST APIs which allows both humans and computers to discover and understand the capabilities of the service without access to source code, documentation, or through network traffic inspection. When properly defined via Swagger, a consumer can understand and interact with the remote service with a minimal amount of implementation logic. Similar to what interfaces have done for lower-level programming, Swagger removes the guesswork in calling the service.

Technically speaking - Swagger is a formal specification surrounded by a large ecosystem of tools, which includes everything from front-end user interfaces, low-level code libraries and commercial API management solutions.

The swagger file can be found here: `hypermap/search_api/static/swagger/search_api.yaml` and will be hosted while Hypermap server is up and running on here `http://localhost/registry/api/docs`

![image](http://panchicore.d.pr/1jk74+)

#### Architecture

The Search API will connect to a dedicated Search backend instance and provide read only search capabilities.

```
  /registry/{catalog_slug}/api/
+---------------------------------+           +----------------------------------+
|                                 |           |                                  |
|   - filter params               |           |                                  |
|   by text, geo, time            |           |                                  |
|   facets params                 |  HTTP     |                                  |
|   - text, geo heatmap,          <----------->                                  |
|   time, username                |           |     Search backend               |
|   - presentation params         |           |                                  |
|   limits, pagination,           |           |                                  |
|   ordering.                     |           |                                  |
|                                 |           |                                  |
+---------------------------------+           +----------------------------------+

```
#### Parameters documentation

As Swagger is the API documentation per se, all filter, facets, presentations parameters, data types, request and response data models, response messages, curl examples, etc,  are described in the Swagger UI  `http://localhost/registry/api/docs` as presented in this screenshot:

![image](http://panchicore.d.pr/1gHWu+)

### 3. Embebed CSW-T

Hypermap has the ability to process CSW Harvest and Transaction requests via CSW-T

pycsw is an OGC CSW server implementation written in Python.

pycsw fully implements the OpenGIS Catalogue Service Implementation Specification (Catalogue Service for the Web). Initial development started in 2010 (more formally announced in 2011). The project is certified OGC Compliant, and is an OGC Reference Implementation.  Since 2015, pycsw is an official OSGeo Project.

Please read the docs at http://docs.pycsw.org/en/2.0.0/ for more information.


#### How to use

The following instructions will show how to use the different requests types:

#### 1. Insert
Insert layers from a XML file located in `data/cswt_insert.xml` with `request=Transaction`, the file contains 10 layers.

```
curl -v -X "POST" \
    "http://admin:admin@localhost/registry/hypermap/csw?service=CSW&request=Transaction" \
     -H "Content-Type: application/xml" \
     -f "data:@data/cswt_insert.xml"
```

#### 1. Retrieve
Return the 10 layers added before with `request=GetRecords`

```
curl -X "GET" \
    "http://admin:admin@localhost/registry/hypermap/csw?service=CSW&version=2.0.2&request=GetRecords&typenames=csw:Record&elementsetname=full&resulttype=results
```

#### 3. Filter layers
Query records with `mode=opensearch` and `q=` parameter, in this example one layer is named "Airport"

```
curl -X "GET" \
    "http://admin:admin@localhost/registry/hypermap/csw?mode=opensearch&service=CSW&version=2.0.2&request=GetRecords&elementsetname=full&typenames=csw:Record&resulttype=results&q=Airport"
```

#### 4. Ensure layers are also indexed in Search backend:
```
curl -X "GET" \
    "http://localhost/_elastic/hypermap/_search"
```
