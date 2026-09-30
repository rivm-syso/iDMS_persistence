#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTANCE_DIR="$(cd "$SCRIPT_DIR/../instance" && pwd)"

source activate flask-rest-test
if [ $? -ne 0 ] ; then
    mamba env create  -f ./envs/flask-rest-test.yaml -q
    source activate flask-rest-test
fi

PGDATA_PATH=$INSTANCE_DIR/database

pg_ctl -D $PGDATA_PATH stop
source deactivate
