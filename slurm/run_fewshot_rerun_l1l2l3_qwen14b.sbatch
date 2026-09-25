#!/bin/bash
# Rerun few-shot (3-shot) for L1-L3 x S1-S3 with qwen2.5-coder-14b-local.
#
# Why rerun:
#   L1/L2: original few-shot examples used 3NF SQL — wrong table/col names for L1/L2
#          schemas. few_shot_examples.json has been manually corrected; old CSVs are
#          deleted below so checkpointing does not skip re-evaluation.
#   L3:    was missing from the original few-shot run.
#
# Output: results/fewshot/<model>__L<sl>S<sem>__fs3.csv  (same dir as original run)

#SBATCH --job-name=fewshot-rerun-l1l2l3-qwen14b
#SBATCH --partition=weics,data-inst
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --mem=128G
#SBATCH --time=72:00:00

set -euo pipefail

SCHEMA_EFFECT_ROOT="${SCHEMA_EFFECT_ROOT:-/group/pmc050/dsu/schema_effect}"
CONFIG="${SCHEMA_EFFECT_ROOT}/slurm/config.env"
RESULTS_DIR="${FEWSHOT_RESULTS_DIR:-results/fewshot}"
MODEL="qwen2.5-coder-14b-local"

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
echo "Model: ${MODEL}"
echo "Conditions: L1S1-S3, L2S1-S3, L3S1-S3"
echo "RESULTS_DIR=${SCHEMA_EFFECT_ROOT}/${RESULTS_DIR}"
echo "LOCAL_LOAD_IN_8BIT=${LOCAL_LOAD_IN_8BIT}"
echo "LOCAL_MAX_NEW_TOKENS=${LOCAL_MAX_NEW_TOKENS}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}"
nvidia-smi || true
echo

# Remove stale L1/L2 CSVs so checkpointing does not skip re-evaluation.
# L3 CSVs don't exist yet so nothing to delete there.
for cond in L1S1 L1S2 L1S3 L2S1 L2S2 L2S3; do
  csv="${SCHEMA_EFFECT_ROOT}/${RESULTS_DIR}/${MODEL}__${cond}__fs3.csv"
  if [[ -f "$csv" ]]; then
    echo "Removing stale: $csv"
    rm "$csv"
  fi
done
echo

python -u run_experiment.py \
  --results-dir "${RESULTS_DIR}" \
  --few-shot 3 \
  --models "${MODEL}" \
  --condition L1S1 --condition L1S2 --condition L1S3 \
  --condition L2S1 --condition L2S2 --condition L2S3 \
  --condition L3S1 --condition L3S2 --condition L3S3

echo
echo "Finished at $(date -Is)"
