#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATION_DIR="$(cd "$SCRIPT_DIR/../migrations" && pwd)"

if [ -d /opt/mambaforge ] ; then
export PATH=/opt/mambaforge/bin:$PATH
fi

if [ -d $HOME/envs/flask-rest ] ; then
export PATH=$HOME/envs/flask-rest/bin:$PATH
fi

for sql_script in $(ls "${MIGRATION_DIR}" | sort)
do
# cat "${MIGRATION_DIR}/$sql_script" | ./runsql.py
echo $sql_script
done
