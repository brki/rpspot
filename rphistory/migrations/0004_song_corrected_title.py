# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-02-18 22:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rphistory', '0003_add_history_song_related_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='song',
            name='corrected_title',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
