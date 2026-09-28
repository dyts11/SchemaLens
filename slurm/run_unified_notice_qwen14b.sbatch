#!/bin/bash
# GPU worker: unified-notice experiment — qwen2.5-coder-14b-local, BIRD.
# Every condition (L1-L6 x S1-S3) gets the SAME prompt template with the
# Deduplication Rules notice (src/denormalization_notice.py:UNIFIED_DENORMALIZATION_NOTICE).
# Submitted by slurm/submit_unified_notice.sh (do not run directly).
#
# One job runs all 18 conditions (run_experiment.py default CONDITIONS).
# Optional env var:
#   NO_NOTICE=1      run the plain template instead → results/no_notice/
#
# Results: results/unified_notice/<model>__L<sl>S<sem>.csv
# Checkpointing built in — safe to resubmit if the job times out.

#SBATCH --cpus-per-task=8

set -euo pipefail

SCHEMA_EFFECT_ROOT="${SCHEMA_EFFECT_ROOT:-/group/pmc050/dsu/schema_effect}"
CONFIG="${SCHEMA_EFFECT_ROOT}/slurm/config.env"
MODEL="qwen2.5-coder-14b-local"

if [[ ! -f "$CONFIG" ]]; then
  echo "Missing ${CONFIG}" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$CONFIG"

# --- notice mode → flag + results dir ---
if [[ "${NO_NOTICE:-0}" == "1" ]]; then
  NOTICE_FLAGS="--no-notice"
  RESULTS_DIR="${SCHEMA_EFFECT_ROOT}/results/no_notice"
else
  NOTICE_FLAGS=""
  RESULTS_DIR="${SCHEMA_EFFECT_ROOT}/results/unified_notice"
fi

export LOCAL_MODELS_DIR
export HF_HOME="${HF_HOME:-${LOCAL_MODELS_DIR}/.cache}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export LOCAL_MAX_NEW_TOKENS="${LOCAL_MAX_NEW_TOKENS:-512}"
export LOCAL_LOAD_IN_8BIT="${LOCAL_LOAD_IN_8BIT:-0}"

source "${VENV_DIR}/bin/activate"
cd "${SCHEMA_EFFECT_ROOT}"

echo "Host: $(hostname)"
echo "Date: $(date -Is)"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-}"
echo "Model: ${MODEL}"
echo "Notice: $([[ -n "${NOTICE_FLAGS}" ]] && echo off || echo 'on (unified, all conditions)')"
echo "Conditions: L1-L6 x S1-S3 (18)"
echo "Results dir: ${RESULTS_DIR}"
echo "LOCAL_LOAD_IN_8BIT=${LOCAL_LOAD_IN_8BIT}"
echo "LOCAL_MAX_NEW_TOKENS=${LOCAL_MAX_NEW_TOKENS}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}"
nvidia-smi || true
echo

# shellcheck disable=SC2086
python -u run_experiment.py \
  --results-dir "${RESULTS_DIR}" \
  --models "${MODEL}" \
  ${NOTICE_FLAGS}

echo
echo "Finished at $(date -Is)"
