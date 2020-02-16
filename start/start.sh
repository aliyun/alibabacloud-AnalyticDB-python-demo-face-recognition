#!/usr/bin/env bash
set -x
DOCKER_IMAGE_NAME=$1
if [ $# -ge 2 ]; then
    APP_PORT=$2
else
    APP_PORT=8000
fi
CONFIG="$(cat ./config.yml)"
docker run --rm -it -p $APP_PORT:$APP_PORT  --env APP_CONFIG="$CONFIG"  ${DOCKER_IMAGE_NAME} sh /home/app/scripts/startup.sh

