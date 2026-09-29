#!/usr/bin/env bash
# Runs a Python script inside the pinned Python 3.9 training environment.
# Puts the pip-installed CUDA 11 libraries (nvidia-*-cu11) on LD_LIBRARY_PATH for TensorFlow 2.8.
# Usage: ml/run_py39.sh <script.py> [args...]   (env location: $VANNAMESCAN_PY39_ENV, default /content/py39)
set -euo pipefail
ENV_DIR="${VANNAMESCAN_PY39_ENV:-/content/py39}"
NVIDIA_LIBS=$(find "$ENV_DIR"/lib/python3.9/site-packages/nvidia -maxdepth 2 -type d -name lib 2>/dev/null | tr '\n' ':' || true)
export LD_LIBRARY_PATH="${NVIDIA_LIBS}${LD_LIBRARY_PATH:-}"
exec "$ENV_DIR/bin/python" "$@"
