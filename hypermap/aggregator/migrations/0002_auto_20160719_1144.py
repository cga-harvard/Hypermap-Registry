# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='layer',
            name='srs',
        ),
        migrations.AddField(
            model_name='service',
            name='srs',
            field=models.ManyToManyField(to='aggregator.SpatialReferenceSystem', null=True, blank=True),
        ),
    ]
