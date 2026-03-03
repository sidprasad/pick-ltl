#!/usr/bin/env bash
set -euo pipefail

export FLASK_APP=pick_ltl.app:app
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
if [ -x ".venv/bin/python" ]; then
  .venv/bin/python -m flask run --debug --port 5000
else
  python -m flask run --debug --port 5000
fi
