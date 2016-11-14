# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0008_alter_cws_last_updated_and_uuid'),
    ]

    operations = [
        migrations.AddField(
            model_name='layer',
            name='was_deleted',
            field=models.BooleanField(default=False),
        ),
    ]
