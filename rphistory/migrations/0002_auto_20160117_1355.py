# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rphistory', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='song',
            name='artist',
        ),
        migrations.AddField(
            model_name='artist',
            name='songs',
            field=models.ManyToManyField(to='rphistory.Song', related_name='artists'),
        ),
    ]
