#!/usr/bin/env sh

pip3 install --upgrade awscli boto3
adduser -S $RUN_USER
mkdir -vp $DIR
chown -R $RUN_USER $DIR
chmod +x $DIR/*
