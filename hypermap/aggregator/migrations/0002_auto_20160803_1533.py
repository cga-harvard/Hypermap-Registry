# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='layer',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-08-03T15:33:14Z', max_length=32),
        ),
        migrations.AddField(
            model_name='service',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-08-03T15:33:14Z', max_length=32),
        ),
    ]
