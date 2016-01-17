# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('trackmap', '0003_handmappedtrack'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='handmappedtrack',
            name='spotify_track_id',
        ),
    ]
