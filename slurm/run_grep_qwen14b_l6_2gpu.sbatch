#!/bin/bash
# Grep (word-overlap) retrieval, L6 only (S1-S3), qwen2.5-coder-14b-local.
# 2 GPUs: L6 schema (JOIN PATHS block) + 3 retrieved examples pushed prompt
# length past what fit in 1 GPU for the other conditions (OOM). No code
# change needed — llm_runner.py already loads the local model with
# device_map="auto", which shards it across all visible GPUs automatically.
# Output: results/grep/<model>__L6S{1,2,3}__grep_fs3.csv
# Checkpointing built in — merges with any existing results/grep/ files from
# a prior 1-GPU run; already-completed rows are skipped.

#SBATCH --job-name=grep-l6-qwen14b-2gpu
#SBATCH --partition=ondemand-gpu
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:2
#SBATCH --mem=128G
#SBATCH --time=12:00:00

set -euo pipefail

SCHEMA_EFFECT_ROOT="${SCHEMA_EFFECT_ROOT:-/group/pmc050/dsu/schema_effect}"
CONFIG="${SCHEMA_EFFECT_ROOT}/slurm/config.env"
RESULTS_DIR="${GREP_RESULTS_DIR:-results/grep}"

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
export LOCAL_LOAD_IN_8BIT="${LOCAL_LOAD_IN_8BIT:-0}"

source "${VENV_DIR}/bin/activate"
cd "${SCHEMA_EFFECT_ROOT}"

echo "Host: $(hostname)"
echo "Date: $(date -Is)"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-}"
echo "Model: qwen2.5-coder-14b-local"
echo "Conditions: L6S1, L6S2, L6S3 only"
echo "Retrieval: top-3, same DB, shared-word count (no term weighting)"
echo "RESULTS_DIR=${SCHEMA_EFFECT_ROOT}/${RESULTS_DIR}"
echo "GPUs requested: 2 (device_map=auto shards the model automatically)"
echo "LOCAL_LOAD_IN_8BIT=${LOCAL_LOAD_IN_8BIT}"
echo "LOCAL_MAX_NEW_TOKENS=${LOCAL_MAX_NEW_TOKENS}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}"
nvidia-smi || true
echo

python -u src/run_experiment_grep.py \
  --results-dir "${RESULTS_DIR}" \
  --models qwen2.5-coder-14b-local \
  --k 3 \
  --condition L6S1 --condition L6S2 --condition L6S3

echo
echo "Finished at $(date -Is)"
