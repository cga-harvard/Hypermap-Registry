# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0002_auto_20160803_1533'),
    ]

    operations = [
        migrations.AddField(
            model_name='layer',
            name='is_monitored',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='layer',
            name='catalogs',
            field=models.ManyToManyField(to='aggregator.Catalog', blank=True),
        ),
        migrations.AlterField(
            model_name='layer',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-08-12T23:56:15Z', max_length=32),
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
            model_name='service',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-08-12T23:56:15Z', max_length=32),
        ),
    ]
