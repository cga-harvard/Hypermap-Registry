# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0011_flag_issues'),
    ]

    operations = [
        migrations.DeleteModel(
            name='TaskError',
        ),
    ]
