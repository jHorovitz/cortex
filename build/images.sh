#!/bin/bash
set -euo pipefail

DIR=$1
IMAGE=$2
CORTEX_VERSION=0.1.0
CORTEX_VERSION_MINOR=0.1
CORTEX_VERSION_MAJOR=0

docker build . -f $DIR/Dockerfile -t cortexlabs/$IMAGE \
                                  -t cortexlabs/$IMAGE:$CORTEX_VERSION \
                                  -t cortexlabs/$IMAGE:$CORTEX_VERSION_MINOR \
                                  -t cortexlabs/$IMAGE:$CORTEX_VERSION_MAJOR

echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin

docker push cortexlabs/$IMAGE:$CORTEX_VERSION
docker push cortexlabs/$IMAGE:$CORTEX_VERSION_MINOR
docker push cortexlabs/$IMAGE:$CORTEX_VERSION_MAJOR
