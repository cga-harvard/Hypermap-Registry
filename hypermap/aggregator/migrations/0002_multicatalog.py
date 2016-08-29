# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='layer',
            name='catalogs',
        ),
        migrations.RemoveField(
            model_name='layer',
            name='srs',
        ),
        migrations.AddField(
            model_name='catalog',
            name='url',
            field=models.URLField(help_text=b'Only if remote. URL where the API for the search backend is served.ex: http://localhost:8000/registry/api/search/', max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='endpoint',
            name='catalog',
            field=models.ForeignKey(default=1, to='aggregator.Catalog'),
        ),
        migrations.AddField(
            model_name='endpointlist',
            name='catalog',
            field=models.ForeignKey(default=1, to='aggregator.Catalog'),
        ),
        migrations.AddField(
            model_name='endpointlist',
            name='greedy',
            field=models.BooleanField(default=False, editable=False),
        ),
        migrations.AddField(
            model_name='layer',
            name='catalog',
            field=models.ForeignKey(default=1, to='aggregator.Catalog'),
        ),
        migrations.AddField(
            model_name='layer',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-08-27T03:13:11Z', max_length=32, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='layer',
            name='is_monitored',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='service',
            name='catalog',
            field=models.ForeignKey(default=1, to='aggregator.Catalog'),
        ),
        migrations.AddField(
            model_name='service',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-08-27T03:13:11Z', max_length=32, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='service',
            name='srs',
            field=models.ManyToManyField(to='aggregator.SpatialReferenceSystem', blank=True),
        ),
        migrations.AlterField(
            model_name='catalog',
            name='name',
            field=models.CharField(help_text=b'Display name in UI', max_length=255),
        ),
        migrations.AlterField(
            model_name='catalog',
            name='slug',
            field=django_extensions.db.fields.AutoSlugField(editable=False, populate_from=b'name', blank=True, help_text=b'Leave empty to be populated from name'),
        ),
        migrations.AlterField(
            model_name='endpoint',
            name='endpoint_list',
            field=models.ForeignKey(blank=True, to='aggregator.EndpointList', null=True),
        ),
        migrations.AlterField(
            model_name='endpoint',
            name='url',
            field=models.URLField(max_length=255),
        ),
        migrations.AlterField(
            model_name='layer',
            name='page_url',
            field=models.URLField(max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='layer',
            name='service',
            field=models.ForeignKey(blank=True, to='aggregator.Service', null=True),
        ),
        migrations.AlterField(
            model_name='layer',
            name='type',
            field=models.CharField(max_length=32, choices=[(b'OGC:CSW', b'Catalogue Service for the Web (CSW)'), (b'OGC:WMS', b'Web Map Service (WMS)'), (b'OGC:WMTS', b'Web Map Tile Service (WMTS)'), (b'OSGeo:TMS', b'Tile Map Service (TMS)'), (b'ESRI:ArcGIS:MapServer', b'ArcGIS REST MapServer'), (b'ESRI:ArcGIS:ImageServer', b'ArcGIS REST ImageServer'), (b'Hypermap:WorldMap', b'Harvard WorldMap'), (b'Hypermap:WARPER', b'Mapwarper')]),
        ),
        migrations.AlterField(
            model_name='service',
            name='type',
            field=models.CharField(max_length=32, choices=[(b'OGC:CSW', b'Catalogue Service for the Web (CSW)'), (b'OGC:WMS', b'Web Map Service (WMS)'), (b'OGC:WMTS', b'Web Map Tile Service (WMTS)'), (b'OSGeo:TMS', b'Tile Map Service (TMS)'), (b'ESRI:ArcGIS:MapServer', b'ArcGIS REST MapServer'), (b'ESRI:ArcGIS:ImageServer', b'ArcGIS REST ImageServer'), (b'Hypermap:WorldMap', b'Harvard WorldMap'), (b'Hypermap:WARPER', b'Mapwarper')]),
        ),
        migrations.AlterUniqueTogether(
            name='endpoint',
            unique_together=set([('url', 'catalog')]),
        ),
    ]
