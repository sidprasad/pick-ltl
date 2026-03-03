#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
echo "Bootstrap complete. Install spot separately with: conda install -c conda-forge spot"

