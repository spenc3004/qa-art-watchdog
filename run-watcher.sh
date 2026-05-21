#!/bin/bash
cd /home/ubuntu/qa-art-watchdog
source /home/ubuntu/qa-art-watchdog/venv/bin/activate
exec /home/ubuntu/qa-art-watchdog/venv/bin/python watcher.py /home/ubuntu/qa-art-watchdog/watching
