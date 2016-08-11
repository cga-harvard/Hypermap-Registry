# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0004_auto_20160809_1938'),
    ]

    operations = [
        migrations.AlterField(
            model_name='catalog',
            name='url',
            field=models.URLField(help_text=b'Only if remote. URL where the API for the search backend is served.ex: http://localhost:8000/registry/api/search/', max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='layer',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-08-11T18:17:36Z', max_length=32, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='service',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-08-11T18:17:36Z', max_length=32, null=True, blank=True),
        ),
    ]
