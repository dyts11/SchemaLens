#!/bin/bash
# DIN-SQL experiment: qwen2.5-coder-14b-local, BIRD, all 18 conditions.
# Per question: 3 LLM calls (schema linking → classification → SQL generation).
# Few-shot examples are the same fixed per-DB examples as the main experiment,
# automatically annotated with schema links and complexity from their gold SQL.
# Output: results/din/<model>__L<sl>S<sem>__din.csv
# Checkpointing built in — already-completed rows are skipped on resume.
#
# Note: 3x LLM calls per question → allow the full 72h walltime.

#SBATCH --job-name=din-qwen14b
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --mem=128G
#SBATCH --time=72:00:00

set -euo pipefail

SCHEMA_EFFECT_ROOT="${SCHEMA_EFFECT_ROOT:-/group/pmc050/dsu/schema_effect}"
CONFIG="${SCHEMA_EFFECT_ROOT}/slurm/config.env"
RESULTS_DIR="${DIN_RESULTS_DIR:-results/din}"

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
echo "Conditions: all 18 (L1-L6 x S1-S3)"
echo "Pipeline: schema linking + classification + SQL generation (3 LLM calls/question)"
echo "RESULTS_DIR=${SCHEMA_EFFECT_ROOT}/${RESULTS_DIR}"
echo "LOCAL_LOAD_IN_8BIT=${LOCAL_LOAD_IN_8BIT}"
echo "LOCAL_MAX_NEW_TOKENS=${LOCAL_MAX_NEW_TOKENS}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}"
nvidia-smi || true
echo

python -u src/run_experiment_din.py \
  --results-dir "${RESULTS_DIR}" \
  --models qwen2.5-coder-14b-local

echo
echo "Finished at $(date -Is)"
