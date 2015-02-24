# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Album',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('title', models.CharField(max_length=255, blank=True)),
                ('asin', models.CharField(max_length=64, unique=True)),
                ('release_year', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Artist',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=255, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='History',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('played_at', models.DateTimeField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Song',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('title', models.CharField(max_length=255)),
                ('rp_song_id', models.IntegerField(unique=True)),
                ('album', models.ForeignKey(to='rphistory.Album', related_name='songs')),
                ('artist', models.ForeignKey(to='rphistory.Artist', related_name='songs')),
            ],
        ),
        migrations.AddField(
            model_name='history',
            name='song',
            field=models.ForeignKey(to='rphistory.Song'),
        ),
    ]
