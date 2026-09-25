#!/bin/bash
# Grep (naive word-overlap) retrieval few-shot experiment: qwen2.5-coder-14b-local, BIRD, L3-L6 x S1-S3 (12 conditions).
# Per question: examples retrieved from dev.json pool (same-DB, top-3 by shared-word count,
# no term weighting), then 1 LLM call to generate SQL. No neural encoder, no BM25/IDF.
# Output: results/grep/<model>__L<sl>S<sem>__grep_fs3.csv
# Checkpointing built in — already-completed rows are skipped on resume.
#
# No extra dependencies (stdlib re only).

#SBATCH --job-name=grep-qwen14b
#SBATCH --partition=ondemand-gpu
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
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
echo "Conditions: L3-L6 x S1-S3 (12 conditions)"
echo "Retrieval: top-3, same DB, shared-word count (no term weighting)"
echo "RESULTS_DIR=${SCHEMA_EFFECT_ROOT}/${RESULTS_DIR}"
echo "LOCAL_LOAD_IN_8BIT=${LOCAL_LOAD_IN_8BIT}"
echo "LOCAL_MAX_NEW_TOKENS=${LOCAL_MAX_NEW_TOKENS}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}"
nvidia-smi || true
echo

python -u src/run_experiment_grep.py \
  --results-dir "${RESULTS_DIR}" \
  --models qwen2.5-coder-14b-local \
  --k 3

echo
echo "Finished at $(date -Is)"
