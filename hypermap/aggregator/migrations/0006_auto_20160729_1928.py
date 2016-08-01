# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0005_remove_catalog_identifier'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='catalog',
            name='api_url',
        ),
        migrations.AddField(
            model_name='catalog',
            name='url_local',
            field=models.CharField(help_text=b'If not remote, add django url name to be reversed', max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='catalog',
            name='url_remote',
            field=models.URLField(help_text=b'Only if remote. URL where the API for the search backend is served. ex: http://localhost:8000/registry/api/search/', max_length=255, null=True, blank=True),
        ),
    ]
