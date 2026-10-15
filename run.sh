#!/bin/bash
# Monthly refresh runner. Called every morning by the job-scout runner (JobScout.app,
# which has Desktop access); build/monthly.py --scheduled only works once a month.
set -u
cd "$(dirname "$0")"
export PATH="/Library/Frameworks/Python.framework/Versions/3.13/bin:/usr/local/bin:/usr/bin:/bin"
mkdir -p data/monthly
echo "$(date "+%F %T") run.sh started" >> data/monthly/run.log
python3 build/monthly.py --scheduled "$@" >> data/monthly/run.log 2>&1
