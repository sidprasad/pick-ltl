#!/usr/bin/env bash
set -euo pipefail

if [ -z "${CONDA_PREFIX:-}" ]; then
  echo "No active Conda environment detected."
  echo "Recommended setup:"
  echo "  conda create -n pick-ltl python=3.12"
  echo "  conda activate pick-ltl"
  echo "  conda install -c conda-forge spot"
  exit 1
fi

python -m pip install -e ".[dev]"
echo "Bootstrap complete in Conda env: ${CONDA_DEFAULT_ENV:-unknown}"
