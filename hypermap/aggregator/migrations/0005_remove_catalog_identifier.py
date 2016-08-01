# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0004_auto_20160722_2041'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='catalog',
            name='identifier',
        ),
    ]
