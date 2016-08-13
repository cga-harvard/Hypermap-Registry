# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='endpoint',
            name='url',
            field=models.URLField(max_length=255),
        ),
        migrations.AlterField(
            model_name='layer',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-08-13T02:22:45Z', max_length=32, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='service',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-08-13T02:22:45Z', max_length=32, null=True, blank=True),
        ),
    ]
