# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0003_uuid'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='is_monitored',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='layer',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-09-05T23:11:51Z', max_length=32, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='service',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-09-05T23:11:51Z', max_length=32, null=True, blank=True),
        ),
    ]
