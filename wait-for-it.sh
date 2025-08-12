#!/bin/bash
# wait-for-it.sh script for Docker services

set -e

host="$1"
shift
cmd="$@"

# Hostname ve port'u ayır
hostname="${host%:*}"
port="${host#*:}"

until nc -z "$hostname" "$port"; do
  >&2 echo "Service is unavailable - sleeping"
  sleep 1
done

>&2 echo "Service is up - executing command"
exec $cmd 