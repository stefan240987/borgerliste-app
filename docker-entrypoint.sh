#!/bin/sh
set -e

mkdir -p /data

# Volumes oprettet af ældre root-containere skal ejes af appuser (uid 1000).
chown -R appuser:appuser /data

exec gosu appuser "$@"
