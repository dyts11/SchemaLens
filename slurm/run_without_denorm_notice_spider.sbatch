#!/bin/bash
# GPU worker: Spider (car_1 + tvshow, 154 questions) L1/L2 without denormalization
# notice, Qwen 14B. Submitted by slurm/submit_without_denorm_notice_spider.sh
#
# Conditions: L1S1-S3 + L2S1-S3 (6, hardcoded in
# src/run_without_denorm_notice_experiment_spider.py, not via SLURM --export).

#SBATCH --job-name=no-denorm-notice-spider-qwen14b
#SBATCH --partition=ondemand-gpu
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --mem=128G
#SBATCH --time=12:00:00

set -euo pipefail

SCHEMA_EFFECT_ROOT="${SCHEMA_EFFECT_ROOT:-/group/pmc050/dsu/schema_effect}"
CONFIG="${SCHEMA_EFFECT_ROOT}/slurm/config.env"

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
echo "SCHEMA_EFFECT_ROOT=${SCHEMA_EFFECT_ROOT}"
echo "LOCAL_MODELS_DIR=${LOCAL_MODELS_DIR}"
echo "LOCAL_LOAD_IN_8BIT=${LOCAL_LOAD_IN_8BIT}"
echo "LOCAL_MAX_NEW_TOKENS=${LOCAL_MAX_NEW_TOKENS}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}"
echo "Dataset: Spider (car_1 + tvshow, 154 questions)"
echo "Conditions: L1S1,L1S2,L1S3,L2S1,L2S2,L2S3 (hardcoded in Python, not via SLURM export)"
echo "Output dir: ${SCHEMA_EFFECT_ROOT}/results/spider/without_denorm_notice/"
nvidia-smi || true
echo

python -m src.run_without_denorm_notice_experiment_spider "$@"

echo
echo "Finished at $(date -Is)"
