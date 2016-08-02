# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0008_auto_20160802_0446'),
    ]

    operations = [
        migrations.AlterField(
            model_name='endpointlist',
            name='catalog',
            field=models.ForeignKey(to='aggregator.Catalog', null=True),
        ),
        migrations.AlterField(
            model_name='layer',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-08-02T23:14:50Z', max_length=32, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='service',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-08-02T23:14:50Z', max_length=32, null=True, blank=True),
        ),
    ]
