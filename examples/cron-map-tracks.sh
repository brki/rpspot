#!/usr/bin/env bash

CRON_LOG=/path/to/cron-logs/load_playlist_$LOGID.log
VENV_PYTHON=/path/to/virtual-env/bin/python
PROJECT_BASE=/path/to/project/base
MAX_TRACKS=150

cd $PROJECT_BASE
echo START $(date) >> $CRON_LOG
$VENV_PYTHON $PROJECT_BASE/manage.py map_tracks --limit $MAX_TRACKS >> $CRON_LOG 2>&1
echo END $(date) >> $CRON_LOG
echo >> $CRON_LOG
