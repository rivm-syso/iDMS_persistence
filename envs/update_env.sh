#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" > /dev/null 2>&1 && pwd )"

mamba env remove -n flask-rest
mamba env update -f ${DIR}/flask-rest.source.yaml 
mamba env export --no-builds -n flask-rest | grep -v ^prefix > ${DIR}/flask-rest.yaml
mamba env remove -n flask-rest-test
mamba env update -f ${DIR}/flask-rest-test.source.yaml 
mamba env export --no-builds -n flask-rest-test | grep -v ^prefix > ${DIR}/flask-rest-test.yaml
