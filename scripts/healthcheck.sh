#!/bin/bash
# Health check script for Docker containers
set -e

SERVICE=${1:-api}

case "$SERVICE" in
    api)
        curl -f http://localhost:8000/api/v1/health || exit 1
        ;;
    postgres)
        pg_isready -U "${POSTGRES_USER:-compmon}" || exit 1
        ;;
    redis)
        redis-cli ping | grep -q PONG || exit 1
        ;;
    mongodb)
        mongosh --eval "db.adminCommand('ping')" --quiet || exit 1
        ;;
    *)
        echo "Unknown service: $SERVICE"
        exit 1
        ;;
esac
