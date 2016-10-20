# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import uuid

def gen_uuid(apps, schema_editor):
    MyModel = apps.get_model('aggregator', 'Layer')
    for row in MyModel.objects.all():
        row.uuid = uuid.uuid4()
        row.save()
    MyModel = apps.get_model('aggregator', 'Service')
    for row in MyModel.objects.all():
        row.uuid = uuid.uuid4()
        row.save()

class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0005_sync_models'),
    ]

    operations = [
        migrations.RunPython(gen_uuid, reverse_code=migrations.RunPython.noop),
    ]
