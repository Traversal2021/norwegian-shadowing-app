#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

RESET=0
SKIP_ASR=0
SKIP_WHISPERX=0

ASR_ENV_NAME="${SHADOWING_ASR_ENV_NAME:-shadowing-asr}"
ASR_PYTHON_VERSION="${SHADOWING_ASR_PYTHON_VERSION:-3.11}"
FASTER_WHISPER_VERSION="${SHADOWING_FASTER_WHISPER_VERSION:-1.1.1}"
REQUESTS_VERSION="${SHADOWING_REQUESTS_VERSION:-2.32.3}"
SPACY_MODEL="${SHADOWING_SPACY_MODEL:-nb_core_news_sm}"

WHISPERX_ENV_NAME="${SHADOWING_WHISPERX_ENV_NAME:-shadowing-whisperx}"
WHISPERX_PYTHON_VERSION="${SHADOWING_WHISPERX_PYTHON_VERSION:-3.10}"
WHISPERX_NUMPY_VERSION="${SHADOWING_WHISPERX_NUMPY_VERSION:-1.26.4}"
WHISPERX_TORCH_VERSION="${SHADOWING_WHISPERX_TORCH_VERSION:-2.0.1}"
WHISPERX_TORCHAUDIO_VERSION="${SHADOWING_WHISPERX_TORCHAUDIO_VERSION:-2.0.2}"
WHISPERX_VERSION="${SHADOWING_WHISPERX_VERSION:-3.1.1}"
WHISPERX_TRANSFORMERS_VERSION="${SHADOWING_WHISPERX_TRANSFORMERS_VERSION:-4.45.2}"
WHISPERX_SETUPTOOLS_VERSION="${SHADOWING_WHISPERX_SETUPTOOLS_VERSION:-80.9.0}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --reset)
      RESET=1
      ;;
    --skip-asr)
      SKIP_ASR=1
      ;;
    --skip-whisperx)
      SKIP_WHISPERX=1
      ;;
    -h|--help)
      cat <<'EOF'
Usage: bash scripts/setup_envs.sh [--reset] [--skip-asr] [--skip-whisperx]

  --reset          Recreate managed environments.
  --skip-asr       Skip the faster-whisper conda environment.
  --skip-whisperx  Skip the WhisperX conda environment.
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
  shift
done

MAIN_STATUS="FAIL"
SPACY_STATUS="FAIL"
FFMPEG_STATUS="FAIL"
ASR_STATUS="WARN"
WHISPERX_STATUS="WARN"
REAL_ALIGNMENT_STATUS="unavailable"
FALLBACK_STATUS="available"

warn() {
  printf 'warning: %s\n' "$*" >&2
}

have_conda() {
  command -v conda >/dev/null 2>&1
}

conda_env_exists() {
  conda env list | awk '{print $1}' | grep -qx "$1"
}

ensure_main_env() {
  if ! command -v python3.12 >/dev/null 2>&1; then
    warn "python3.12 is required to create .venv. Install Python 3.12 and rerun."
    return 1
  fi

  if [[ $RESET -eq 1 && -d .venv ]]; then
    rm -rf .venv
  fi

  if [[ ! -d .venv ]]; then
    echo "Creating main project environment in .venv"
    python3.12 -m venv .venv || return 1
  fi

  if ! .venv/bin/python -m pip install --upgrade pip setuptools wheel; then
    return 1
  fi
  if ! .venv/bin/python -m pip install "numpy==1.26.4"; then
    return 1
  fi
  if ! .venv/bin/python -m pip install -e "tools/pipeline[segmentation]"; then
    return 1
  fi
  if ! .venv/bin/python -m spacy download "$SPACY_MODEL"; then
    return 1
  fi
  if ! .venv/bin/python - <<'PY'
import importlib.util
import sys
import numpy
import spacy
import os

assert sys.version_info[:2] == (3, 12), sys.version
assert numpy.__version__ == "1.26.4", numpy.__version__
spacy.load(os.environ.get("SHADOWING_SPACY_MODEL", "nb_core_news_sm"))
assert importlib.util.find_spec("torch") is None
assert importlib.util.find_spec("whisperx") is None
assert importlib.util.find_spec("faster_whisper") is None
PY
  then
    return 1
  fi

  MAIN_STATUS="OK"
  SPACY_STATUS="OK"
  return 0
}

ensure_ffmpeg() {
  if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
    FFMPEG_STATUS="OK"
    return 0
  fi
  FFMPEG_STATUS="FAIL"
  warn "ffmpeg/ffprobe not found. Install them with: brew install ffmpeg"
  return 1
}

setup_asr_env() {
  if [[ $SKIP_ASR -eq 1 ]]; then
    ASR_STATUS="WARN"
    return 0
  fi
  if ! have_conda; then
    ASR_STATUS="WARN"
    warn "conda was not found. faster-whisper alignment will be unavailable."
    return 1
  fi

  if [[ $RESET -eq 1 ]]; then
    conda env remove -n "$ASR_ENV_NAME" -y >/dev/null 2>&1 || true
  fi

  if ! conda_env_exists "$ASR_ENV_NAME"; then
    echo "Creating faster-whisper environment: $ASR_ENV_NAME"
    if ! conda create -y -n "$ASR_ENV_NAME" "python=${ASR_PYTHON_VERSION}"; then
      ASR_STATUS="FAIL"
      warn "failed to create faster-whisper conda env $ASR_ENV_NAME."
      return 1
    fi
  fi

  echo "Installing faster-whisper stack in $ASR_ENV_NAME"
  if ! conda run -n "$ASR_ENV_NAME" python -m pip install --upgrade pip setuptools wheel; then
    ASR_STATUS="FAIL"
    return 1
  fi
  if ! conda run -n "$ASR_ENV_NAME" python -m pip install \
      "requests==${REQUESTS_VERSION}" \
      "faster-whisper==${FASTER_WHISPER_VERSION}"; then
    ASR_STATUS="WARN"
    warn "faster-whisper installation failed. Real alignment will rely on other backends if available."
    return 1
  fi
  if ! conda run -n "$ASR_ENV_NAME" python -c "import faster_whisper; print('faster-whisper import ok')" >/dev/null 2>&1; then
    ASR_STATUS="WARN"
    warn "faster-whisper import failed after installation."
    return 1
  fi
  if ! conda run -n "$ASR_ENV_NAME" python tools/alignment/faster_whisper_runner.py --self-check >/dev/null 2>&1; then
    ASR_STATUS="WARN"
    warn "faster-whisper runner self-check failed."
    return 1
  fi

  ASR_STATUS="OK"
  REAL_ALIGNMENT_STATUS="available"
  return 0
}

setup_whisperx_env() {
  if [[ $SKIP_WHISPERX -eq 1 ]]; then
    WHISPERX_STATUS="WARN"
    return 0
  fi
  if ! have_conda; then
    WHISPERX_STATUS="WARN"
    warn "conda was not found. WhisperX alignment will be unavailable."
    return 1
  fi

  if [[ $RESET -eq 1 ]]; then
    conda env remove -n "$WHISPERX_ENV_NAME" -y >/dev/null 2>&1 || true
  fi

  if ! conda_env_exists "$WHISPERX_ENV_NAME"; then
    echo "Creating WhisperX environment: $WHISPERX_ENV_NAME"
    if ! conda create -y -n "$WHISPERX_ENV_NAME" "python=${WHISPERX_PYTHON_VERSION}"; then
      WHISPERX_STATUS="FAIL"
      warn "failed to create WhisperX conda env $WHISPERX_ENV_NAME."
      return 1
    fi
  fi

  echo "Installing WhisperX stack in $WHISPERX_ENV_NAME"
  echo "Pinned stack: python=${WHISPERX_PYTHON_VERSION}, numpy==${WHISPERX_NUMPY_VERSION}, torch==${WHISPERX_TORCH_VERSION}, torchaudio==${WHISPERX_TORCHAUDIO_VERSION}, transformers==${WHISPERX_TRANSFORMERS_VERSION}, whisperx==${WHISPERX_VERSION}"
  if ! conda run -n "$WHISPERX_ENV_NAME" python -m pip install --upgrade pip wheel "setuptools==${WHISPERX_SETUPTOOLS_VERSION}"; then
    WHISPERX_STATUS="FAIL"
    return 1
  fi
  if ! conda run -n "$WHISPERX_ENV_NAME" python -m pip install \
      "numpy==${WHISPERX_NUMPY_VERSION}" \
      "torch==${WHISPERX_TORCH_VERSION}" \
      "torchaudio==${WHISPERX_TORCHAUDIO_VERSION}" \
      "transformers==${WHISPERX_TRANSFORMERS_VERSION}" \
      "whisperx==${WHISPERX_VERSION}"; then
    WHISPERX_STATUS="WARN"
    warn "WhisperX dependency installation failed."
    return 1
  fi
  if ! conda run -n "$WHISPERX_ENV_NAME" python -c "import whisperx; print('whisperx import ok')" >/dev/null 2>&1; then
    WHISPERX_STATUS="WARN"
    warn "WhisperX import failed after installation."
    return 1
  fi
  if ! conda run -n "$WHISPERX_ENV_NAME" python tools/alignment/whisperx_runner.py --self-check >/dev/null 2>&1; then
    WHISPERX_STATUS="WARN"
    warn "WhisperX runner self-check failed."
    return 1
  fi

  WHISPERX_STATUS="OK"
  REAL_ALIGNMENT_STATUS="available"
  return 0
}

ensure_main_env || MAIN_STATUS="FAIL"
ensure_ffmpeg || true
setup_asr_env || true
setup_whisperx_env || true

printf '\nStatus\n'
printf '%-24s %s\n' "main .venv:" "$MAIN_STATUS"
printf '%-24s %s\n' "spaCy segmentation:" "$SPACY_STATUS"
printf '%-24s %s\n' "ffmpeg:" "$FFMPEG_STATUS"
printf '%-24s %s\n' "faster-whisper env:" "$ASR_STATUS"
printf '%-24s %s\n' "WhisperX env:" "$WHISPERX_STATUS"
printf '%-24s %s\n' "fallback ingestion:" "$FALLBACK_STATUS"
printf '%-24s %s\n' "real alignment:" "$REAL_ALIGNMENT_STATUS"

if [[ "$MAIN_STATUS" != "OK" ]]; then
  exit 1
fi
