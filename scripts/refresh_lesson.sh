#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

cd "$REPO_ROOT"
PYTHONPATH=tools/pipeline/src python3 -m shadowing_pipeline.cli build "$@"
sh scripts/sync_lessons_to_web.sh
