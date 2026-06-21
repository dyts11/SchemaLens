#!/usr/bin/env bash
# Download all local models to LOCAL_MODELS_DIR on Kaya (group node / login node).
#
# Kaya layout:
#   Project:  /group/pmc050/dsu/schema_effect
#   Weights:  /group/pmc050/dsu/schema_effect/hub/{Qwen2.5-Coder-14B-Instruct,...}
#
# Usage (on Kaya, from project root):
#   source .venv/bin/activate   # first time: pip install -r requirements-local.txt
#   bash slurm/download_models.sh
#
# Set HF_TOKEN in slurm/config.env if a model is gated.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${SCRIPT_DIR}/config.env"

if [[ ! -f "$CONFIG" ]]; then
  echo "Missing ${CONFIG}. Copy slurm/config.env.example to slurm/config.env." >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$CONFIG"

if [[ -z "${LOCAL_MODELS_DIR:-}" ]]; then
  echo "LOCAL_MODELS_DIR is not set in ${CONFIG}" >&2
  exit 1
fi

mkdir -p "$LOCAL_MODELS_DIR"
mkdir -p "${PIP_CACHE_DIR:-${LOCAL_MODELS_DIR}/../.pip-cache}"
mkdir -p "${TMPDIR:-${LOCAL_MODELS_DIR}/../tmp}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-${SCHEMA_EFFECT_ROOT}/../.pip-cache}"
export TMPDIR="${TMPDIR:-${SCHEMA_EFFECT_ROOT}/../tmp}"
export HF_HOME="${HF_HOME:-${LOCAL_MODELS_DIR}/.cache}"
mkdir -p "$PIP_CACHE_DIR" "$TMPDIR" "$HF_HOME"

if [[ -n "${VENV_DIR:-}" && -f "${VENV_DIR}/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "${VENV_DIR}/bin/activate"
  echo "Using venv: ${VENV_DIR}"
fi

hf_download() {
  if command -v huggingface-cli >/dev/null 2>&1; then
    huggingface-cli download "$@"
    return
  fi
  if command -v hf >/dev/null 2>&1; then
    hf download "$@"
    return
  fi
  if command -v python >/dev/null 2>&1; then
    python -m huggingface_hub.cli.huggingface_cli download "$@"
    return
  fi
  echo "huggingface-cli not found." >&2
  echo "Activate your venv and install:" >&2
  echo "  source ${VENV_DIR:-.venv}/bin/activate" >&2
  echo "  pip install huggingface_hub" >&2
  exit 1
}

download_one() {
  local repo="$1"
  local subdir="$2"
  local dest="${LOCAL_MODELS_DIR}/${subdir}"

  if [[ -f "${dest}/config.json" ]]; then
    echo "[skip] already present: ${dest}"
    return 0
  fi

  echo "[download] ${repo} -> ${dest}"
  hf_download "$repo" --local-dir "$dest"
}

echo "LOCAL_MODELS_DIR=${LOCAL_MODELS_DIR}"
echo

download_one "Qwen/Qwen2.5-Coder-0.5B-Instruct"  "Qwen2.5-Coder-0.5B-Instruct"
download_one "Qwen/Qwen2.5-Coder-1.5B-Instruct"  "Qwen2.5-Coder-1.5B-Instruct"
download_one "Qwen/Qwen2.5-Coder-3B-Instruct"     "Qwen2.5-Coder-3B-Instruct"
download_one "Qwen/Qwen2.5-Coder-7B-Instruct"     "Qwen2.5-Coder-7B-Instruct"
download_one "Qwen/Qwen2.5-Coder-14B-Instruct"    "Qwen2.5-Coder-14B-Instruct"
download_one "Qwen/Qwen2.5-Coder-32B-Instruct"    "Qwen2.5-Coder-32B-Instruct"
download_one "microsoft/phi-4"                     "phi-4"
download_one "allenai/Olmo-2-1124-13B-Instruct"   "Olmo-2-1124-13B-Instruct"

echo
echo "Done. Weights under: ${LOCAL_MODELS_DIR}"
