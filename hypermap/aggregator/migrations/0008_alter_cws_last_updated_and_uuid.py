# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import uuid
import hypermap.aggregator.models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0007_remove_uuid_null'),
    ]

    operations = [
        migrations.AlterField(
            model_name='layer',
            name='csw_last_updated',
            field=models.CharField(default=hypermap.aggregator.models.get_default_now_as_string, max_length=32, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='layer',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='service',
            name='csw_last_updated',
            field=models.CharField(default=hypermap.aggregator.models.get_default_now_as_string, max_length=32, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='service',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
    ]
