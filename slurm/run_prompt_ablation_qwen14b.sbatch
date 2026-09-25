#!/bin/bash
# GPU worker: prompt ablation experiment — qwen2.5-coder-14b-local, BIRD.
# Submitted by slurm/submit_prompt_ablation.sh (do not run directly).
#
# Required env vars (set by submit script):
#   VARIANT          cot | ev | cot_ev
#   CONDITION_GROUP  l1l2 | l4l5l6
#
# Results written to results/<variant>/<model>__L<sl>S<sem>__<suffix>.csv
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

# --- Resolve VARIANT → flags + results dir ---
case "${VARIANT:?VARIANT env var is required (cot|ev|cot_ev)}" in
  cot)
    VARIANT_FLAGS="--cot"
    RESULTS_DIR="${SCHEMA_EFFECT_ROOT}/results/cot"
    ;;
  ev)
    VARIANT_FLAGS="--evidence"
    RESULTS_DIR="${SCHEMA_EFFECT_ROOT}/results/ev"
    ;;
  cot_ev)
    VARIANT_FLAGS="--cot --evidence"
    RESULTS_DIR="${SCHEMA_EFFECT_ROOT}/results/cot_ev"
    ;;
  *)
    echo "Unknown VARIANT '${VARIANT}'. Expected: cot | ev | cot_ev" >&2
    exit 1
    ;;
esac

# --- Resolve CONDITION_GROUP → --condition flags ---
case "${CONDITION_GROUP:?CONDITION_GROUP env var is required (l1l2|l4l5l6)}" in
  l1l2)
    # 6 conditions: L1 x S1-S3 + L2 x S1-S3
    CONDITION_FLAGS="--condition L1S1 --condition L1S2 --condition L1S3 \
--condition L2S1 --condition L2S2 --condition L2S3"
    ;;
  l3l4l5l6)
    # 12 conditions: L3-L6 x S1-S3
    CONDITION_FLAGS="--condition L3S1 --condition L3S2 --condition L3S3 \
--condition L4S1 --condition L4S2 --condition L4S3 \
--condition L5S1 --condition L5S2 --condition L5S3 \
--condition L6S1 --condition L6S2 --condition L6S3"
    ;;
  *)
    echo "Unknown CONDITION_GROUP '${CONDITION_GROUP}'. Expected: l1l2 | l3l4l5l6" >&2
    exit 1
    ;;
esac

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
echo "Variant: ${VARIANT}  (flags: ${VARIANT_FLAGS})"
echo "Condition group: ${CONDITION_GROUP}"
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
  ${CONDITION_FLAGS} \
  ${VARIANT_FLAGS}

echo
echo "Finished at $(date -Is)"
