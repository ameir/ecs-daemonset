#!/usr/bin/env sh

set -aeu

AWS_DEFAULT_REGION=${AWS_REGION:-us-east-1}
: ${ECS_CLUSTER_NAME:=default}
: ${RESOURCE_CHECK_INTERVAL:=60}

./$APP_NAME.py --cluster $ECS_CLUSTER_NAME
