#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTANCE_DIR="$(cd "$SCRIPT_DIR/instance" && pwd)"

source activate flask-rest-test
if [ $? -ne 0 ] ; then
    mamba env create  -f ./envs/flask-rest-test.yaml -q
    source activate flask-rest-test
fi

export BIO_REST_INSTANCE_PATH="$INSTANCE_DIR"
export FLASK_APP="idms.persistence:create_app()"
export PYTHONPATH="src:$PYTHONPATH"
export FLASK_ENV=development
PORT=6${UID: -3}
# PORT=8080

sh scripts/start_db.sh

echo Run app on port $PORT
flask run --host=0.0.0.0 --port=$PORT

sh scripts/stop_db.sh

