#!/usr/bin/env bash

TYPE="$1"

if [ "$TYPE" == "now" ]; then
   LOGID=now
   PLAYLIST=now.xml
elif [ "$TYPE" == "full" ]; then
   LOGID=full
   PLAYLIST=playlist.xml
elif [ "$TYPE" == "four" ]; then
   LOGID=four
   PLAYLIST=now_4.xml
else
   echo "Unknown TYPE parameter received, valid values are: now, full, four"
   exit 1
fi

CRON_LOG=/path/to/cron-logs/load_playlist_$LOGID.log
VENV_PYTHON=/path/to/virtual-env/bin/python
PROJECT_BASE=/path/to/project/base

cd $PROJECT_BASE
echo START $(date) >> $CRON_LOG
$VENV_PYTHON $PROJECT_BASE/manage.py load_playlist --playlist $PLAYLIST >> $CRON_LOG 2>&1
echo END $(date) >> $CRON_LOG
echo >> $CRON_LOG
