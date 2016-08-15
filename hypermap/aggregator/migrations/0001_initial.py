# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import taggit.managers
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0002_auto_20150616_2121'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Catalog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'Display name in UI', max_length=255)),
                ('slug', django_extensions.db.fields.AutoSlugField(editable=False, populate_from=b'name', blank=True, help_text=b'Leave empty to be populated from name')),
                ('url', models.URLField(help_text=b'Only if remote. URL where the API for the search backend is served.ex: http://localhost:8000/registry/api/search/', max_length=255, null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Check',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField()),
                ('checked_datetime', models.DateTimeField(auto_now=True)),
                ('success', models.BooleanField(default=False)),
                ('response_time', models.FloatField()),
                ('message', models.TextField(default=b'OK')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
            ],
        ),
        migrations.CreateModel(
            name='Endpoint',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('processed', models.BooleanField(default=False)),
                ('processed_datetime', models.DateTimeField(auto_now=True)),
                ('imported', models.BooleanField(default=False)),
                ('message', models.TextField(null=True, blank=True)),
                ('url', models.URLField(max_length=255)),
                ('catalog', models.ForeignKey(default=1, editable=False, to='aggregator.Catalog')),
            ],
        ),
        migrations.CreateModel(
            name='EndpointList',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('upload', models.FileField(upload_to=b'endpoint_lists')),
                ('greedy', models.BooleanField(default=False)),
                ('catalog', models.ForeignKey(default=1, editable=False, to='aggregator.Catalog')),
            ],
        ),
        migrations.CreateModel(
            name='Layer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255, null=True, blank=True)),
                ('abstract', models.TextField(null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('active', models.BooleanField(default=True)),
                ('url', models.URLField(max_length=255)),
                ('is_public', models.BooleanField(default=True)),
                ('type', models.CharField(max_length=32, choices=[(b'OGC:CSW', b'Catalogue Service for the Web (CSW)'), (b'OGC:WMS', b'Web Map Service (WMS)'), (b'OGC:WMTS', b'Web Map Tile Service (WMTS)'), (b'OSGeo:TMS', b'Tile Map Service (TMS)'), (b'ESRI:ArcGIS:MapServer', b'ArcGIS REST MapServer'), (b'ESRI:ArcGIS:ImageServer', b'ArcGIS REST ImageServer'), (b'Hypermap:WorldMap', b'Harvard WorldMap'), (b'Hypermap:WARPER', b'Mapwarper')])),
                ('temporal_extent_start', models.CharField(max_length=255, null=True, blank=True)),
                ('temporal_extent_end', models.CharField(max_length=255, null=True, blank=True)),
                ('csw_last_updated', models.CharField(default=b'2016-08-15T20:18:14Z', max_length=32, null=True, blank=True)),
                ('csw_type', models.CharField(default=b'dataset', max_length=32)),
                ('csw_typename', models.CharField(default=b'csw:Record', max_length=32)),
                ('csw_schema', models.CharField(default=b'http://www.opengis.net/cat/csw/2.0.2', max_length=64)),
                ('anytext', models.TextField(null=True, blank=True)),
                ('wkt_geometry', models.TextField(default=b'POLYGON((-180 -90,-180 90,180 90,180 -90,-180 -90))')),
                ('xml', models.TextField(default=b'<csw:Record xmlns:csw="http://www.opengis.net/cat/2.0.2"/>', null=True, blank=True)),
                ('name', models.CharField(max_length=255, null=True, blank=True)),
                ('bbox_x0', models.DecimalField(null=True, max_digits=19, decimal_places=10, blank=True)),
                ('bbox_x1', models.DecimalField(null=True, max_digits=19, decimal_places=10, blank=True)),
                ('bbox_y0', models.DecimalField(null=True, max_digits=19, decimal_places=10, blank=True)),
                ('bbox_y1', models.DecimalField(null=True, max_digits=19, decimal_places=10, blank=True)),
                ('thumbnail', models.ImageField(null=True, upload_to=b'layers', blank=True)),
                ('page_url', models.URLField(max_length=255, null=True, blank=True)),
                ('is_monitored', models.BooleanField(default=True)),
                ('catalog', models.ForeignKey(default=1, editable=False, to='aggregator.Catalog')),
                ('keywords', taggit.managers.TaggableManager(to='taggit.Tag', through='taggit.TaggedItem', blank=True, help_text='A comma-separated list of tags.', verbose_name='Tags')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='LayerDate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.CharField(max_length=25)),
                ('type', models.IntegerField(choices=[(0, b'Detected'), (1, b'From Metadata')])),
                ('layer', models.ForeignKey(to='aggregator.Layer')),
            ],
        ),
        migrations.CreateModel(
            name='LayerWM',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('category', models.CharField(max_length=255, null=True, blank=True)),
                ('username', models.CharField(max_length=255, null=True, blank=True)),
                ('temporal_extent_start', models.CharField(max_length=255, null=True, blank=True)),
                ('temporal_extent_end', models.CharField(max_length=255, null=True, blank=True)),
                ('layer', models.OneToOneField(to='aggregator.Layer')),
            ],
            options={
                'verbose_name': 'WorldMap Layer Attributes',
                'verbose_name_plural': 'WorldMap Layers Attributes',
            },
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255, null=True, blank=True)),
                ('abstract', models.TextField(null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('active', models.BooleanField(default=True)),
                ('url', models.URLField(max_length=255)),
                ('is_public', models.BooleanField(default=True)),
                ('type', models.CharField(max_length=32, choices=[(b'OGC:CSW', b'Catalogue Service for the Web (CSW)'), (b'OGC:WMS', b'Web Map Service (WMS)'), (b'OGC:WMTS', b'Web Map Tile Service (WMTS)'), (b'OSGeo:TMS', b'Tile Map Service (TMS)'), (b'ESRI:ArcGIS:MapServer', b'ArcGIS REST MapServer'), (b'ESRI:ArcGIS:ImageServer', b'ArcGIS REST ImageServer'), (b'Hypermap:WorldMap', b'Harvard WorldMap'), (b'Hypermap:WARPER', b'Mapwarper')])),
                ('temporal_extent_start', models.CharField(max_length=255, null=True, blank=True)),
                ('temporal_extent_end', models.CharField(max_length=255, null=True, blank=True)),
                ('csw_last_updated', models.CharField(default=b'2016-08-15T20:18:14Z', max_length=32, null=True, blank=True)),
                ('csw_type', models.CharField(default=b'dataset', max_length=32)),
                ('csw_typename', models.CharField(default=b'csw:Record', max_length=32)),
                ('csw_schema', models.CharField(default=b'http://www.opengis.net/cat/csw/2.0.2', max_length=64)),
                ('anytext', models.TextField(null=True, blank=True)),
                ('wkt_geometry', models.TextField(default=b'POLYGON((-180 -90,-180 90,180 90,180 -90,-180 -90))')),
                ('xml', models.TextField(default=b'<csw:Record xmlns:csw="http://www.opengis.net/cat/2.0.2"/>', null=True, blank=True)),
                ('catalog', models.ForeignKey(default=1, editable=False, to='aggregator.Catalog')),
                ('keywords', taggit.managers.TaggableManager(to='taggit.Tag', through='taggit.TaggedItem', blank=True, help_text='A comma-separated list of tags.', verbose_name='Tags')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SpatialReferenceSystem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=255, null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='TaskError',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('task_name', models.CharField(max_length=255)),
                ('args', models.CharField(max_length=255)),
                ('error_datetime', models.DateTimeField(auto_now=True)),
                ('message', models.TextField(null=True, blank=True)),
            ],
        ),
        migrations.AddField(
            model_name='service',
            name='srs',
            field=models.ManyToManyField(to='aggregator.SpatialReferenceSystem', blank=True),
        ),
        migrations.AddField(
            model_name='layer',
            name='service',
            field=models.ForeignKey(blank=True, to='aggregator.Service', null=True),
        ),
        migrations.AddField(
            model_name='endpoint',
            name='endpoint_list',
            field=models.ForeignKey(blank=True, to='aggregator.EndpointList', null=True),
        ),
        migrations.AlterUniqueTogether(
            name='endpoint',
            unique_together=set([('url', 'catalog')]),
        ),
    ]
