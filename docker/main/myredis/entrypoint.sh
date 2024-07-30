#!/usr/bin/env sh

# Determine REDIS_PASS from Docker secret, with the secret name provided via the DOCKER_SECRET_REDIS_PASS env variable
SECRET_FILE="/run/secrets/${DOCKER_SECRET_REDIS_PASS:?}"
REDIS_PASS="$(cat ${SECRET_FILE})"

redis-server /usr/local/etc/redis/redis.conf --requirepass "${REDIS_PASS:?}"
