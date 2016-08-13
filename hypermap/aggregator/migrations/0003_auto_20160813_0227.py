# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0002_auto_20160813_0222'),
    ]

    operations = [
        migrations.AlterField(
            model_name='layer',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-08-13T02:27:30Z', max_length=32, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='service',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-08-13T02:27:30Z', max_length=32, null=True, blank=True),
        ),
        migrations.AlterUniqueTogether(
            name='endpoint',
            unique_together=set([('url', 'catalog')]),
        ),
    ]
