#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source activate flask-rest
if [ $? -ne 0 ] ; then
    mamba env create  -f ../envs/flask-rest.yaml -q
    source activate flask-rest
fi

python $SCRIPT_DIR/notify.py

source deactivate

