# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rphistory', '0001_initial'),
        ('trackmap', '0002_trackavailability_score'),
    ]

    operations = [
        migrations.CreateModel(
            name='HandmappedTrack',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('spotify_track_id', models.CharField(max_length=120, help_text='Spotify track id')),
                ('info_url', models.CharField(max_length=255, help_text='URL to resource with information about album', blank=True)),
                ('processed', models.BooleanField(default=False)),
                ('rp_song', models.OneToOneField(related_name='handmapped_track', to='rphistory.Song')),
            ],
        ),
    ]
