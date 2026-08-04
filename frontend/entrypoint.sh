#!/bin/sh
# Custom entrypoint to process nginx template with proper defaults

set -e

# Set default API URL if not provided or invalid
if [ -z "$RAILWAY_SERVICE_FLUXWALL_URL" ] || ! echo "$RAILWAY_SERVICE_FLUXWALL_URL" | grep -q '^https\?://'; then
    export RAILWAY_SERVICE_FLUXWALL_URL="http://fluxwall.railway.internal:8000"
fi

# Process template with envsubst
envsubst '${RAILWAY_SERVICE_FLUXWALL_URL}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

# Execute original nginx entrypoint
exec /docker-entrypoint.sh "$@"