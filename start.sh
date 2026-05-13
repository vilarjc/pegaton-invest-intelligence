#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "Starting PEGATON server..."
nohup python backend/app/main.py > /tmp/pegaton_server.log 2>&1 &
echo "PID: $!"
