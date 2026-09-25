#!/bin/bash
# GPU worker: WAMEX held-out set (149 questions), all 18 conditions (L1-L6 x S1-S3).
# Submitted by slurm/submit_wamex.sh
#
# Conditions are passed explicitly (independent of CONDITIONS in run_experiment.py).

#SBATCH --cpus-per-task=8

set -euo pipefail

SCHEMA_EFFECT_ROOT="${SCHEMA_EFFECT_ROOT:-/group/pmc050/dsu/schema_effect}"
CONFIG="${SCHEMA_EFFECT_ROOT}/slurm/config.env"
SPIDER_DIR="${WAMEX_DIR:-dev_20240627/wamex_data}"
QUESTIONS="${WAMEX_QUESTIONS:-${SPIDER_DIR}/experiment_questions_wamex.json}"
RESULTS_DIR="${WAMEX_RESULTS_DIR:-results/wamex}"

if [[ ! -f "$CONFIG" ]]; then
  echo "Missing ${CONFIG}" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$CONFIG"

if [[ -z "${MODEL:-}" ]]; then
  echo "MODEL env var is required (set by submit script)" >&2
  exit 1
fi

export LOCAL_MODELS_DIR
export HF_HOME="${HF_HOME:-${LOCAL_MODELS_DIR}/.cache}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export LOCAL_MAX_NEW_TOKENS="${LOCAL_MAX_NEW_TOKENS:-512}"

source "${VENV_DIR}/bin/activate"
cd "${SCHEMA_EFFECT_ROOT}"

echo "Host: $(hostname)"
echo "Date: $(date -Is)"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-}"
echo "MODEL=${MODEL}"
echo "SPIDER_DIR=${SPIDER_DIR}"
echo "RESULTS_DIR=${RESULTS_DIR}"
echo "Conditions: L1-L6 x S1-S3 (18, passed explicitly)"
echo "Questions: ${QUESTIONS}"
echo "SCHEMA_EFFECT_ROOT=${SCHEMA_EFFECT_ROOT}"
echo "LOCAL_MODELS_DIR=${LOCAL_MODELS_DIR}"
echo "LOCAL_LOAD_IN_8BIT=${LOCAL_LOAD_IN_8BIT:-}"
echo "LOCAL_MAX_NEW_TOKENS=${LOCAL_MAX_NEW_TOKENS}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}"
nvidia-smi || true
echo

CONDITION_ARGS=()
for l in 1 2 3 4 5 6; do
  for s in 1 2 3; do
    CONDITION_ARGS+=(--condition "L${l}S${s}")
  done
done

python -u run_experiment.py \
  --spider-dir "${SPIDER_DIR}" \
  --questions "${QUESTIONS}" \
  --results-dir "${RESULTS_DIR}" \
  "${CONDITION_ARGS[@]}" \
  --models "${MODEL}"

echo
echo "Finished ${MODEL} at $(date -Is)"
