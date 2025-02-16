#!/bin/bash
if [ -f .pid ]; then
    pid=$(cat .pid)
    kill $pid
    rm .pid
    echo "Options scanner stopped."
else
    echo "PID file not found."
fi 