#!/bin/bash
# Reflexion experiment: qwen2.5-coder-14b-local, BIRD, all 18 conditions, 1 reflexion round.
# Per question: 1 initial call + up to 2 more (reflect + correct) if incorrect.
# Output: results/reflexion/<model>__L<sl>S<sem>__reflexion1.csv
# Checkpointing built in — already-completed rows are skipped on resume.

#SBATCH --job-name=reflexion-qwen14b
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --mem=128G
#SBATCH --time=72:00:00

set -euo pipefail

SCHEMA_EFFECT_ROOT="${SCHEMA_EFFECT_ROOT:-/group/pmc050/dsu/schema_effect}"
CONFIG="${SCHEMA_EFFECT_ROOT}/slurm/config.env"
RESULTS_DIR="${REFLEXION_RESULTS_DIR:-results/reflexion}"

if [[ ! -f "$CONFIG" ]]; then
  echo "Missing ${CONFIG}" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$CONFIG"

export LOCAL_MODELS_DIR
export HF_HOME="${HF_HOME:-${LOCAL_MODELS_DIR}/.cache}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
# Increase token budget vs standard runs: reflection step generates verbose
# diagnostic text before the correction step produces SQL.
export LOCAL_MAX_NEW_TOKENS="${LOCAL_MAX_NEW_TOKENS:-1024}"
# 14b fits in bf16 on H100 (≈28 GB VRAM) — 8-bit not required.
export LOCAL_LOAD_IN_8BIT="${LOCAL_LOAD_IN_8BIT:-0}"

source "${VENV_DIR}/bin/activate"
cd "${SCHEMA_EFFECT_ROOT}"

echo "Host: $(hostname)"
echo "Date: $(date -Is)"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-}"
echo "Model: qwen2.5-coder-14b-local"
echo "Conditions: all 18 (L1-L6 x S1-S3)"
echo "Reflexion rounds: 1"
echo "RESULTS_DIR=${SCHEMA_EFFECT_ROOT}/${RESULTS_DIR}"
echo "LOCAL_LOAD_IN_8BIT=${LOCAL_LOAD_IN_8BIT}"
echo "LOCAL_MAX_NEW_TOKENS=${LOCAL_MAX_NEW_TOKENS}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}"
nvidia-smi || true
echo

python -u src/run_experiment_reflexion.py \
  --results-dir "${RESULTS_DIR}" \
  --models qwen2.5-coder-14b-local \
  --max-rounds 1

echo
echo "Finished at $(date -Is)"
