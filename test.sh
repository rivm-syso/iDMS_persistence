#!/bin/bash

export GIT_SSL_NO_VERIFY=true

source activate flask-rest-test
if [ $? -ne 0 ] ; then
    conda env create  -f ./envs/flask-rest-test.yaml -q
    source activate flask-rest-test
fi

# Test if we are runnning in docker
echo TEST

echo "CI_SERVER: [${CI_SERVER}]"

if [ "${CI_SERVER}" = "yes" ] ; then
    echo Add postgres user
    useradd -ms /bin/bash postgres
    export RUN_AS_ROOT="yes"
else
    echo "Run as $USER, because CI_SERVER=$CI_SERVER"
    export RUN_AS_ROOT="no"
fi

# Create a test postgres instance
mkdir -p test/data
rm -rf test/data/*

export INITDB=`which initdb`
export PG_CTL=`which pg_ctl`

echo "Initialize and start postgres"
if [ "$RUN_AS_ROOT" = "yes" ] ; then
    chmod 777 /tmp
    chown postgres test/data
    su postgres -c "$INITDB --auth-host=trust -D test/data -U postgres"
else
    initdb --auth-host=trust -D test/data -U postgres
fi
cp test/cfg/postgresql.conf test/data
if [ "$RUN_AS_ROOT" = "yes" ] ; then
    su postgres -c "$PG_CTL -D test/data -l logfile start"
else
    pg_ctl -D test/data -l logfile start
fi

psql -h /tmp -p 9876 -U postgres --file test/cfg/initialize.sql
# Initialize DB
SCRIPTDIR=scripts

for a in $(ls "${SCRIPTDIR}" | sort)
do
cat "${SCRIPTDIR}/$a" | psql -h /tmp -p 9876 -U postgres
done

# PYTHONPATH=$(pwd) pytest -v $@
# RESULT=$?

# pg_ctl -D test/data stop
# rm -rf test/data/*

# exit $RESULT


