# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0012_delete_taskerror'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='check',
            options={'ordering': ['-checked_datetime']},
        ),
    ]
