#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTANCE_DIR="$(cd "$SCRIPT_DIR/../instance" && pwd)"
TEST_DIR="$(cd "$SCRIPT_DIR/../test" && pwd)"
MIGRATION_DIR="$(cd "$SCRIPT_DIR/../migrations" && pwd)"

source activate flask-rest-test
if [ $? -ne 0 ] ; then
    mamba env create  -f ./envs/flask-rest-test.yaml -q
    source activate flask-rest-test
fi

PGDATA_PATH=$INSTANCE_DIR/database

# Create a test postgres instance
if [ ! -d "$PGDATA_PATH" ]; then
    mkdir -p $PGDATA_PATH

    export INITDB=`which initdb`
    export PG_CTL=`which pg_ctl`

    echo "Initialize and start postgres"
    initdb --auth-host=trust -D $PGDATA_PATH -U postgres
    cp $TEST_DIR/cfg/postgresql.conf $PGDATA_PATH
    pg_ctl -D $PGDATA_PATH -l instance/db_logfile start

    psql -h /tmp -p 9876 -U postgres --file $TEST_DIR/cfg/initialize.sql
else
    pg_ctl -D $PGDATA_PATH -l $INSTANCE_DIR/db_logfile start
fi

# Initialize DB
for sql_script in $(ls "${MIGRATION_DIR}" | sort)
do
    cat "${MIGRATION_DIR}/$sql_script" | psql -h /tmp -p 9876 -U postgres
done