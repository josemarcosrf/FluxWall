#!/bin/sh
# Custom entrypoint to inject FLUXWALL_API_URL into the nginx config template.
# The default targets the docker-compose backend service; override the var to
# point at your API (e.g. Railway: http://fluxwall.railway.internal:8000).

set -e

: "${FLUXWALL_API_URL:=http://api:8000}"
export FLUXWALL_API_URL

# Process template with envsubst
envsubst '${FLUXWALL_API_URL}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

# Execute original nginx entrypoint
exec /docker-entrypoint.sh "$@"