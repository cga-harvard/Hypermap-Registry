# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='endpointlist',
            name='greedy',
            field=models.BooleanField(default=False),
        ),
    ]
