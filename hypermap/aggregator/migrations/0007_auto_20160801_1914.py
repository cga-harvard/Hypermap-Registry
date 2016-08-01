# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('aggregator', '0006_auto_20160729_1928'),
    ]

    operations = [
        migrations.AddField(
            model_name='layer',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-08-01T19:14:10Z', max_length=32),
        ),
        migrations.AddField(
            model_name='service',
            name='csw_last_updated',
            field=models.CharField(default=b'2016-08-01T19:14:10Z', max_length=32),
        ),
        migrations.AlterField(
            model_name='catalog',
            name='slug',
            field=django_extensions.db.fields.AutoSlugField(editable=False, populate_from=b'name', blank=True, help_text=b'Leave empty to be populated from name'),
        ),
        migrations.AlterField(
            model_name='endpoint',
            name='catalog',
            field=models.ForeignKey(blank=True, to='aggregator.Catalog', null=True),
        ),
        migrations.AlterField(
            model_name='endpointlist',
            name='catalog',
            field=models.ForeignKey(blank=True, to='aggregator.Catalog', null=True),
        ),
        migrations.AlterField(
            model_name='layer',
            name='catalog',
            field=models.ForeignKey(blank=True, to='aggregator.Catalog', null=True),
        ),
    ]
