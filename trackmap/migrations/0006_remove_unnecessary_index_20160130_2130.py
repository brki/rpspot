# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re

from django.db import migrations, models

def drop_varchar_pattern_ops_index(apps, schemaEditor):
    """
    Remove the varchar_pattern_ops index (which is good for doing like searches), since this column
    will not be used for like searches.
    """
    model = apps.get_model("trackmap", "TrackAvailability")
    index_names = schemaEditor._constraint_names(model, index=True)
    for index_name in index_names:
        if re.search('trackmap_trackavailability_country_.+_like', index_name):
            print('dropping index {}'.format(index_name))
            schemaEditor.execute(schemaEditor._delete_constraint_sql(schemaEditor.sql_delete_index, model, index_name))


class Migration(migrations.Migration):

    dependencies = [
        ('trackmap', '0005_add_trackavailability-country_index_20160130_2121'),
    ]

    operations = [
        migrations.RunPython(
            drop_varchar_pattern_ops_index
        ),
    ]
