#!/bin/bash
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || { echo "รัน ./install.command ก่อน"; exit 1; }
exec .venv/bin/python -m speakaj "$@"
