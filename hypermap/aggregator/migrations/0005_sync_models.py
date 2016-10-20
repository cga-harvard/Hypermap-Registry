# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0004_is_monitored'),
    ]

    operations = [
        migrations.AlterField(
            model_name='layer',
            name='bbox_x0',
            field=models.DecimalField(default=-180, null=True, max_digits=19, decimal_places=10, blank=True),
        ),
        migrations.AlterField(
            model_name='layer',
            name='bbox_x1',
            field=models.DecimalField(default=180, null=True, max_digits=19, decimal_places=10, blank=True),
        ),
        migrations.AlterField(
            model_name='layer',
            name='bbox_y0',
            field=models.DecimalField(default=-90, null=True, max_digits=19, decimal_places=10, blank=True),
        ),
        migrations.AlterField(
            model_name='layer',
            name='bbox_y1',
            field=models.DecimalField(default=90, null=True, max_digits=19, decimal_places=10, blank=True),
        ),
        migrations.AlterField(
            model_name='layer',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-10-20T20:08:58Z', max_length=32, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='layer',
            name='type',
            field=models.CharField(default=b'OGC:WMS', max_length=32, choices=[(b'OGC:CSW', b'Catalogue Service for the Web (CSW)'), (b'OGC:WMS', b'Web Map Service (WMS)'), (b'OGC:WMTS', b'Web Map Tile Service (WMTS)'), (b'OSGeo:TMS', b'Tile Map Service (TMS)'), (b'ESRI:ArcGIS:MapServer', b'ArcGIS REST MapServer'), (b'ESRI:ArcGIS:ImageServer', b'ArcGIS REST ImageServer'), (b'Hypermap:WorldMap', b'Harvard WorldMap'), (b'Hypermap:WARPER', b'Mapwarper')]),
        ),
        migrations.AlterField(
            model_name='service',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-10-20T20:08:58Z', max_length=32, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='service',
            name='type',
            field=models.CharField(default=b'OGC:WMS', max_length=32, choices=[(b'OGC:CSW', b'Catalogue Service for the Web (CSW)'), (b'OGC:WMS', b'Web Map Service (WMS)'), (b'OGC:WMTS', b'Web Map Tile Service (WMTS)'), (b'OSGeo:TMS', b'Tile Map Service (TMS)'), (b'ESRI:ArcGIS:MapServer', b'ArcGIS REST MapServer'), (b'ESRI:ArcGIS:ImageServer', b'ArcGIS REST ImageServer'), (b'Hypermap:WorldMap', b'Harvard WorldMap'), (b'Hypermap:WARPER', b'Mapwarper')]),
        ),
    ]
