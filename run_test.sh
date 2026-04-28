#!/bin/bash
set -eo pipefail

export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export CI=true

cd /workspace/docker-android/cli
mkdir -p test-results
pytest -v --tb=short -p no:cacheprovider --no-cov -o "addopts="

