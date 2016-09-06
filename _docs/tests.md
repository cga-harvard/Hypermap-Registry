# Testing

## Creating layers

- **WMS testing:** Upload http://demo.opengeo.org/geoserver/wms. There should be 72 layers created and indexed in search backend.
- Modify environment variable REGISTRY_LIMIT_LAYERS to 2. If you are using Docker, modify your docker-compose.yml file for both django and celery docker images and verify that no service has more than 2 layers.
- Verify that the number of layers created in the database and documents indexed in search backend are the same.
- the total number when the map UI client is loaded matches the total number of records in elasticsearch and the total number of layers in registry's home page.

## Service detail page.

- Using a previously generated service from an endpoint, remove checks using **Remove Checks** button. Then press Check now button and verify in the celery monitor tab that check task is run. After the check is finished  you can verify the number of total checks in the *monitoring period* section.
![image](https://cloud.githubusercontent.com/assets/3285923/17679102/91ec62b6-62ff-11e6-8672-4dfe306c7aa6.png)

![image](http://d.pr/i/16v0E+)

## Celery monitor and search backend indexing

- Using a previously created service. Verify that all layers are indexed in search backend. For elasticsearch you can verify executing this commmand in terminal.
```sh
    curl http://localhost:9200/_cat/indices?v
```
- To remove documents in the search backend, press *clear index* button. And verify that there are not document indexed in the given index.
- Press *Reindex all layers* to add all created layers into the search backend. And verify in the search backend.
![image](https://cloud.githubusercontent.com/assets/3285923/17679268/584b7faa-6300-11e6-9bf3-31007ca6ce8f.png)
![image](http://d.pr/i/P0I1+)

## CSW Transaction test

Using Created Makefile, run csw transactions test

```sh
make test-csw-transactions
```

You should see the result shown in the figure below

![image](https://cloud.githubusercontent.com/assets/3285923/18269953/3495dbe0-73f0-11e6-90a2-38785b9beeaa.png)


