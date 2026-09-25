#!/bin/bash
# Spider rerun: qwen2.5-coder-32b-local, remaining conditions after L4S2 timeout.
# Conditions: L4S3, L5S1-S3, L6S1-S3 (7 conditions x 154 questions).
# Checkpointing built in — already-completed rows are skipped automatically.

#SBATCH --job-name=spider-rerun-qwen32b
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --mem=128G
#SBATCH --time=72:00:00

set -euo pipefail

SCHEMA_EFFECT_ROOT="${SCHEMA_EFFECT_ROOT:-/group/pmc050/dsu/schema_effect}"
CONFIG="${SCHEMA_EFFECT_ROOT}/slurm/config.env"
SPIDER_DIR="${SPIDER_DIR:-dev_20240627/spider_data}"
RESULTS_DIR="${SPIDER_RESULTS_DIR:-results/spider}"

if [[ ! -f "$CONFIG" ]]; then
  echo "Missing ${CONFIG}" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$CONFIG"

export LOCAL_MODELS_DIR
export HF_HOME="${HF_HOME:-${LOCAL_MODELS_DIR}/.cache}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export LOCAL_MAX_NEW_TOKENS="${LOCAL_MAX_NEW_TOKENS:-512}"
export LOCAL_LOAD_IN_8BIT=0

source "${VENV_DIR}/bin/activate"
cd "${SCHEMA_EFFECT_ROOT}"

echo "Host: $(hostname)"
echo "Date: $(date -Is)"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-}"
echo "Model: qwen2.5-coder-32b-local"
echo "Conditions: L4S3, L5S1, L5S2, L5S3, L6S1, L6S2, L6S3"
echo "SPIDER_DIR=${SPIDER_DIR}"
echo "RESULTS_DIR=${RESULTS_DIR}"
echo "LOCAL_LOAD_IN_8BIT=${LOCAL_LOAD_IN_8BIT}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}"
nvidia-smi || true
echo

python -u run_experiment.py \
  --spider-dir "${SPIDER_DIR}" \
  --results-dir "${RESULTS_DIR}" \
  --models qwen2.5-coder-32b-local \
  --condition L4S3 \
  --condition L5S1 \
  --condition L5S2 \
  --condition L5S3 \
  --condition L6S1 \
  --condition L6S2 \
  --condition L6S3

echo
echo "Finished at $(date -Is)"
