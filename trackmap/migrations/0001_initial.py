# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rphistory', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Album',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('spotify_id', models.CharField(max_length=120, unique=True, help_text='A spotify album id')),
                ('title', models.CharField(max_length=255, help_text='Album title')),
                ('img_small_url', models.URLField(null=True)),
                ('img_medium_url', models.URLField(null=True)),
                ('img_large_url', models.URLField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Track',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('spotify_id', models.CharField(max_length=120, unique=True, help_text='A spotify track id')),
                ('title', models.CharField(max_length=255, help_text='Track title')),
                ('artist', models.CharField(max_length=255, help_text='Primary artist name')),
                ('artist_id', models.CharField(max_length=120, help_text='A spotify artist id')),
                ('many_artists', models.BooleanField(default=False)),
                ('album', models.ForeignKey(to='trackmap.Album')),
            ],
        ),
        migrations.CreateModel(
            name='TrackAvailability',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('country', models.CharField(max_length=2)),
                ('rp_song', models.ForeignKey(to='rphistory.Song', related_name='available_tracks')),
                ('track', models.ForeignKey(to='trackmap.Track')),
            ],
        ),
        migrations.CreateModel(
            name='TrackSearchHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('search_time', models.DateTimeField()),
                ('found', models.BooleanField(default=False)),
                ('rp_song', models.OneToOneField(to='rphistory.Song', related_name='search_history')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='trackavailability',
            unique_together=set([('track', 'rp_song', 'country')]),
        ),
    ]
