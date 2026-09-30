#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" > /dev/null 2>&1 && pwd )"

cd $DIR

source activate flask-rest
if [ $? -ne 0 ] ; then
conda env update -f ${DIR}/envs/flask-rest.yaml
source activate flask-rest
fi

. db_migrate.sh

