# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0009_layer_was_deleted'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='layer',
            options={'ordering': ['name']},
        ),
        migrations.AddField(
            model_name='layer',
            name='is_valid',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='service',
            name='is_valid',
            field=models.BooleanField(default=True),
        ),
    ]
