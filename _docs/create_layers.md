# Create layers from endpoint

In hhypermap registry it is possible to harvest map services in different ways. You can create services using a single endpoint or creating a list of endpoints. and endpoint could be defined as a server's url address of services required for harvesting. You can find a good resource for endpoints in http://hh.worldmap.harvard.edu/)

![image](https://cloud.githubusercontent.com/assets/3285923/17596743/693d5392-5fb8-11e6-9a1d-5873295f1563.png)
*Application index page*

## Accessing the administration panel.

Assuming that you have hhypermap registry installed and running in your development/production server (including fixtures), enter in your browser the url: http://your_url/registry. For my case, because I am running in a development server, the url corresponds to http://localhost:8000/registry. The request response will be the page seen above.

In order to access to the administration panel, in your browser enter http://localhost:8000/admin. Access through your credentials (**user:** admin, **password:** admin). The server will respond with the administrative panel page (See figure below)

![image](https://cloud.githubusercontent.com/assets/3285923/17597227/86e11dfa-5fba-11e6-80db-a5417c42a1e2.png)
*Administrative panel*

## Harvest services from a single endpoint

HHypermap registry is designed to create a service that contains information layers given a single endpoint url. To perform this, in the administrative panel, aggregator section, select Endpoints options. There you can check which endpoints have been added before and some other options. To add other endpoints, press the button *Add endpoint*. The server will respond with the pages that is shown below.

![image](https://cloud.githubusercontent.com/assets/3285923/17601195/8bf6fe24-5fcc-11e6-8b19-6ec08bcaa1dd.png)
*Add new endpoint page response*

![image](https://cloud.githubusercontent.com/assets/3285923/17606021/f0484be2-5fe2-11e6-930b-e29f4d959a8e.png)
*Adding a new endpoint to the database*

The required fields to add an endpoint are *url* and *catalog*. After a new endpoint is aggregated into the database, the celery workers start the harvesting process. Hhypermap Registry fetches layers from a service, generates thumbnails and index each layer metadata to the search backend.
![image](https://cloud.githubusercontent.com/assets/3285923/17606202/dbd00690-5fe3-11e6-866d-b97c17a2eb4a.png)

Now you can check in the hhypermap registry page the created service and layers.

![image](https://cloud.githubusercontent.com/assets/3285923/17606743/c42c4b2c-5fe6-11e6-89f3-b7a921dba0bc.png)

## Harvest services from an endpointlist

Hhypermap registry has the ability to start the harvesting process of services, giving a list of endpoints within a text file. This text file must have on each line a service endpoint. For example:

```
http://worldmap.harvard.edu/ 
http://warp.worldmap.harvard.edu/maps
http://servicesig102.lehavre.fr/arcgi...
```

Now, go to the administrative panel, Endpoint list section, add endpoint list. There, you upload the file, select catalog and press save. After this, the application starts harvesting layers for each service independently and adds them into the search backend.

**Note:** Arcgis services have the option to fetch information layers from multiple endpoints within a folder. HHypermap registry comes with the option to create layers from a folder, giving only one of the endpoints that belong to the respective folder. This is possible checking the **greedy** option.

