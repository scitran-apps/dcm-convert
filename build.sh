#!/bin/bash
# Builds the container.

CONTAINER=scitran/dcm-convert:v1.1.0
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
docker build --no-cache --tag $CONTAINER $DIR
