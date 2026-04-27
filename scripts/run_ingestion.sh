#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

ALIGNER="auto"
FORCE=0
LESSON_ID=""
RUN_ALL=0
ASR_ENV_NAME="${SHADOWING_ASR_ENV_NAME:-shadowing-asr}"
WHISPERX_ENV_NAME="${SHADOWING_WHISPERX_ENV_NAME:-shadowing-whisperx}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/run_ingestion.sh --lesson <lesson-id> [--aligner auto|fallback|fastwhisper|whisperx] [--force]
  bash scripts/run_ingestion.sh --all [--aligner auto|fallback|fastwhisper|whisperx] [--force]
EOF
}

runner_available() {
  env_name="$1"
  runner_path="$2"
  command -v conda >/dev/null 2>&1 || return 1
  conda env list | awk '{print $1}' | grep -qx "$env_name" || return 1
  conda run -n "$env_name" python "$runner_path" --self-check >/dev/null 2>&1
}

runner_failure_reason() {
  env_name="$1"
  runner_path="$2"
  if ! command -v conda >/dev/null 2>&1; then
    printf 'conda is not on PATH'
    return 0
  fi
  if ! conda env list | awk '{print $1}' | grep -qx "$env_name"; then
    printf "conda env '%s' does not exist" "$env_name"
    return 0
  fi
  conda run -n "$env_name" python "$runner_path" --self-check >/tmp/shadowing-runner-check.$$ 2>&1 || true
  reason="$(tail -n 1 /tmp/shadowing-runner-check.$$ 2>/dev/null || cat /tmp/shadowing-runner-check.$$ 2>/dev/null || true)"
  rm -f /tmp/shadowing-runner-check.$$
  if [[ -z "$reason" ]]; then
    reason="runner self-check failed"
  fi
  printf '%s' "$reason"
}

print_summary() {
  report_path="$1"
  if [[ ! -f "$report_path" ]]; then
    echo "error: build report missing after refresh: $report_path" >&2
    return 1
  fi

  summary_lines="$(PYTHONPATH=tools/pipeline/src .venv/bin/python - <<PY
import json
from pathlib import Path

payload = json.loads(Path("$report_path").read_text(encoding="utf-8"))
alignment = payload.get("alignment", {})
print(payload.get("lessonId", ""))
print(alignment.get("alignerUsed", ""))
print(str(alignment.get("fallbackOccurred", False)).lower())
print(alignment.get("externalAlignmentPath", "") or "")
print(str(Path("apps/web/public/lessons") / payload.get("lessonId", "")).strip())
PY
)"
  lesson_name="$(printf '%s\n' "$summary_lines" | sed -n '1p')"
  aligner_used="$(printf '%s\n' "$summary_lines" | sed -n '2p')"
  fallback_used="$(printf '%s\n' "$summary_lines" | sed -n '3p')"
  external_path="$(printf '%s\n' "$summary_lines" | sed -n '4p')"
  web_path="$(printf '%s\n' "$summary_lines" | sed -n '5p')"

  echo
  echo "Lesson: $lesson_name"
  echo "Aligner requested: $ALIGNER"
  echo "Aligner used: $aligner_used"
  echo "Fallback occurred: $fallback_used"
  if [[ -n "$external_path" ]]; then
    echo "External alignment: $external_path"
  fi
  echo "Web files: $web_path"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lesson)
      LESSON_ID="${2:-}"
      shift
      ;;
    --all)
      RUN_ALL=1
      ;;
    --aligner)
      ALIGNER="${2:-}"
      shift
      ;;
    --force)
      FORCE=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

if [[ ! -x .venv/bin/python ]]; then
  echo "error: .venv is missing. Run: bash scripts/setup_envs.sh" >&2
  exit 1
fi

if [[ $RUN_ALL -eq 1 && -n "$LESSON_ID" ]]; then
  echo "error: use either --lesson or --all, not both." >&2
  exit 1
fi
if [[ $RUN_ALL -eq 0 && -z "$LESSON_ID" ]]; then
  echo "error: pass --lesson <lesson-id> or --all." >&2
  exit 1
fi
case "$ALIGNER" in
  auto|fallback|fastwhisper|whisperx)
    ;;
  *)
    echo "error: --aligner must be auto, fallback, fastwhisper, or whisperx." >&2
    exit 1
    ;;
esac

if [[ $RUN_ALL -eq 0 && ! -d "content/raw/$LESSON_ID" ]]; then
  echo "error: lesson does not exist: content/raw/$LESSON_ID" >&2
  exit 1
fi

unset SHADOWING_FASTWHISPER_CMD || true
unset SHADOWING_WHISPERX_CMD || true

FASTWHISPER_RUNNER="$REPO_ROOT/tools/alignment/faster_whisper_runner.py"
WHISPERX_RUNNER="$REPO_ROOT/tools/alignment/whisperx_runner.py"

FASTWHISPER_AVAILABLE=0
WHISPERX_AVAILABLE=0
if [[ "$ALIGNER" != "fallback" ]]; then
  if runner_available "$ASR_ENV_NAME" "$FASTWHISPER_RUNNER"; then
    FASTWHISPER_AVAILABLE=1
    export SHADOWING_FASTWHISPER_CMD="conda run --no-capture-output -n ${ASR_ENV_NAME} python ${FASTWHISPER_RUNNER}"
  fi
  if runner_available "$WHISPERX_ENV_NAME" "$WHISPERX_RUNNER"; then
    WHISPERX_AVAILABLE=1
    export SHADOWING_WHISPERX_CMD="conda run --no-capture-output -n ${WHISPERX_ENV_NAME} python ${WHISPERX_RUNNER}"
  fi
fi

if [[ "$ALIGNER" == "fastwhisper" && $FASTWHISPER_AVAILABLE -ne 1 ]]; then
  reason="$(runner_failure_reason "$ASR_ENV_NAME" "$FASTWHISPER_RUNNER")"
  echo "error: faster-whisper aligner was requested, but '$ASR_ENV_NAME' is unavailable: $reason" >&2
  echo "Run: bash scripts/setup_envs.sh" >&2
  exit 1
fi
if [[ "$ALIGNER" == "whisperx" && $WHISPERX_AVAILABLE -ne 1 ]]; then
  reason="$(runner_failure_reason "$WHISPERX_ENV_NAME" "$WHISPERX_RUNNER")"
  echo "error: WhisperX aligner was requested, but '$WHISPERX_ENV_NAME' is unavailable: $reason" >&2
  echo "Run: bash scripts/setup_envs.sh" >&2
  exit 1
fi
if [[ "$ALIGNER" == "auto" && $FASTWHISPER_AVAILABLE -ne 1 ]]; then
  fastwhisper_reason="$(runner_failure_reason "$ASR_ENV_NAME" "$FASTWHISPER_RUNNER")"
  if [[ $WHISPERX_AVAILABLE -eq 1 ]]; then
    echo "warning: faster-whisper runner is unavailable ($fastwhisper_reason); auto mode will try WhisperX next." >&2
  else
    echo "warning: no external real-aligner runner is available; faster-whisper check failed: $fastwhisper_reason" >&2
  fi
fi

ARGS=()
if [[ $RUN_ALL -eq 1 ]]; then
  ARGS+=(--all)
else
  ARGS+=(--lesson "$LESSON_ID")
fi
if [[ $FORCE -eq 1 ]]; then
  ARGS+=(--force)
fi

case "$ALIGNER" in
  fallback)
    ARGS+=(--aligner fallback)
    ;;
  auto)
    ARGS+=(--aligner auto)
    ;;
  fastwhisper)
    ARGS+=(--aligner fastwhisper)
    ;;
  whisperx)
    ARGS+=(--aligner whisperx)
    ;;
esac

PYTHONPATH=tools/pipeline/src .venv/bin/python -m shadowing_pipeline.cli refresh "${ARGS[@]}"

if [[ $RUN_ALL -eq 1 ]]; then
  find content/raw -mindepth 1 -maxdepth 1 -type d | sort | while IFS= read -r lesson_dir; do
    print_summary "content/processed/$(basename "$lesson_dir")/build-report.json"
  done
else
  print_summary "content/processed/${LESSON_ID}/build-report.json"
fi

echo
echo "Run the web app with: npm run web:dev"
