#!/bin/sh
set -e

python -m pip install --no-cache-dir -r /app/requirements.txt
exec python /app/server.py
