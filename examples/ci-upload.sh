#!/usr/bin/env sh
set -eu

: "${FSERVER_URL:?set FSERVER_URL, for example https://f-server.example.com}"
: "${FSERVER_API_KEY:?set FSERVER_API_KEY}"

apk="${1:?usage: examples/ci-upload.sh path/to/app.apk}"
metadata="${2:-{\"release_channel\":\"release\"}}"

curl --fail-with-body \
  -H "Authorization: Bearer ${FSERVER_API_KEY}" \
  -F "apk=@${apk};type=application/vnd.android.package-archive" \
  -F "metadata=${metadata}" \
  "${FSERVER_URL%/}/api/v1/upload"
