# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0003_merge'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='layer',
            name='catalogs',
        ),
        migrations.AddField(
            model_name='catalog',
            name='api_url',
            field=models.URLField(default='http://localhost', help_text=b'URL where the API for the search backend is served. ex: http://localhost:8000/registry/api/search/', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='catalog',
            name='identifier',
            field=models.CharField(help_text=b'Identifier string in search backend. AKA: indice or core name. ex: hypermap', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='endpoint',
            name='catalog',
            field=models.ForeignKey(to='aggregator.Catalog', blank=True, null=True),
        ),
        migrations.AddField(
            model_name='endpointlist',
            name='catalog',
            field=models.ForeignKey(to='aggregator.Catalog', blank=True, null=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='layer',
            name='catalog',
            field=models.ForeignKey(to='aggregator.Catalog', blank=True, null=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='service',
            name='catalog',
            field=models.ForeignKey(to='aggregator.Catalog', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='catalog',
            name='name',
            field=models.CharField(help_text=b'Display name in UI', max_length=255),
        ),
        migrations.AlterField(
            model_name='endpoint',
            name='endpoint_list',
            field=models.ForeignKey(to='aggregator.EndpointList', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='layer',
            name='type',
            field=models.CharField(max_length=32, choices=[(b'OGC:CSW', b'Catalogue Service for the Web (CSW)'), (b'OGC:WMS', b'Web Map Service (WMS)'), (b'OGC:WMTS', b'Web Map Tile Service (WMTS)'), (b'OSGeo:TMS', b'Tile Map Service (TMS)'), (b'ESRI:ArcGIS:MapServer', b'ArcGIS REST MapServer'), (b'ESRI:ArcGIS:ImageServer', b'ArcGIS REST ImageServer'), (b'Hypermap:WorldMap', b'Harvard WorldMap'), (b'Hypermap:WARPER', b'Mapwarper')]),
        ),
        migrations.AlterField(
            model_name='service',
            name='srs',
            field=models.ManyToManyField(to='aggregator.SpatialReferenceSystem', blank=True),
        ),
        migrations.AlterField(
            model_name='service',
            name='type',
            field=models.CharField(max_length=32, choices=[(b'OGC:CSW', b'Catalogue Service for the Web (CSW)'), (b'OGC:WMS', b'Web Map Service (WMS)'), (b'OGC:WMTS', b'Web Map Tile Service (WMTS)'), (b'OSGeo:TMS', b'Tile Map Service (TMS)'), (b'ESRI:ArcGIS:MapServer', b'ArcGIS REST MapServer'), (b'ESRI:ArcGIS:ImageServer', b'ArcGIS REST ImageServer'), (b'Hypermap:WorldMap', b'Harvard WorldMap'), (b'Hypermap:WARPER', b'Mapwarper')]),
        ),
    ]
