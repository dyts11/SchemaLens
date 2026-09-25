#!/bin/bash
# Dense retrieval few-shot experiment: qwen2.5-coder-14b-local, BIRD, L3-L6 x S1-S3 (12 conditions).
# Per question: embeddings retrieved from dev.json pool (same-DB, top-3 by cosine sim),
# then 1 LLM call to generate SQL.
# Output: results/dense/<model>__L<sl>S<sem>__dense_fs3.csv
# Checkpointing built in — already-completed rows are skipped on resume.
#
# Pool embeddings are cached to dev_20240627/embeddings_cache/ on first run (~1 min).
# Requires sentence-transformers in venv:
#   pip install sentence-transformers>=3.0.0

#SBATCH --job-name=dense-qwen14b
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --mem=128G
#SBATCH --time=72:00:00

set -euo pipefail

SCHEMA_EFFECT_ROOT="${SCHEMA_EFFECT_ROOT:-/group/pmc050/dsu/schema_effect}"
CONFIG="${SCHEMA_EFFECT_ROOT}/slurm/config.env"
RESULTS_DIR="${DENSE_RESULTS_DIR:-results/dense}"

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
echo "Retrieval: top-3, same DB, cosine similarity (all-MiniLM-L6-v2)"
echo "RESULTS_DIR=${SCHEMA_EFFECT_ROOT}/${RESULTS_DIR}"
echo "LOCAL_LOAD_IN_8BIT=${LOCAL_LOAD_IN_8BIT}"
echo "LOCAL_MAX_NEW_TOKENS=${LOCAL_MAX_NEW_TOKENS}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}"
nvidia-smi || true
echo

python -u src/run_experiment_dense.py \
  --results-dir "${RESULTS_DIR}" \
  --models qwen2.5-coder-14b-local \
  --k 3

echo
echo "Finished at $(date -Is)"
