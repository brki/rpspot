# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-01-30 21:21
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trackmap', '0004_remove_handmappedtrack_spotify_track_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trackavailability',
            name='country',
            field=models.CharField(db_index=True, max_length=2),
        ),
    ]
