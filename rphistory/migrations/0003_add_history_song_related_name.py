# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-02-18 17:49
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rphistory', '0002_auto_20160117_1355'),
    ]

    operations = [
        migrations.AlterField(
            model_name='history',
            name='song',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='history', to='rphistory.Song'),
        ),
    ]
