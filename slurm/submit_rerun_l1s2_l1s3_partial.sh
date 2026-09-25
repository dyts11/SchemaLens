#!/usr/bin/env bash
# Submit L1S2+L1S3 for 7B, 14B, phi-4 (L1S1 already done).
# One job per model, 2 GPUs each, fp16 sharded via device_map="auto".
#
# Usage:
#   cd /group/pmc050/dsu/schema_effect
#   bash slurm/submit_rerun_l1s2_l1s3_partial.sh
#
# Dry-run:
#   DRY_RUN=1 bash slurm/submit_rerun_l1s2_l1s3_partial.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${SCRIPT_DIR}/config.env"
DRY_RUN="${DRY_RUN:-0}"
SUBMITTED=0
FAILED=0

if [[ ! -f "$CONFIG" ]]; then
  echo "Missing ${CONFIG}. Copy slurm/config.env.example to slurm/config.env." >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$CONFIG"

LOG_DIR="${SCHEMA_EFFECT_ROOT}/slurm/logs"
mkdir -p "$LOG_DIR"

# model | semantic_levels | gpus | mem_gb | walltime | load_8bit (0=fp16, 1=8bit)
SPECS=(
  "qwen2.5-coder-7b-local|2,3|2|64|12:00:00|0"
  "qwen2.5-coder-14b-local|2,3|2|128|16:00:00|0"
  "phi-4-local|2,3|2|128|16:00:00|0"
)

GPU_PARTITION="${SLURM_PARTITION:-gpu}"

echo "Host: $(hostname)"
echo "RERUN_DB_ID=${RERUN_DB_ID}"
echo "Partial rerun: L1S2+L1S3 only, 1 job per model, 2 GPUs each"
echo

SBATCH_EXTRA=()

if [[ -n "${SLURM_ACCOUNT:-}" ]]; then
  SBATCH_EXTRA+=(--account="${SLURM_ACCOUNT}")
fi
SBATCH_EXTRA+=(--partition="${GPU_PARTITION}")
if [[ -n "${SLURM_QOS:-}" ]]; then
  SBATCH_EXTRA+=(--qos="${SLURM_QOS}")
fi

for spec in "${SPECS[@]}"; do
  IFS='|' read -r model sem_levels gpus mem walltime load_8bit <<< "$spec"
  job_name="rerun-${RERUN_DB_ID}-${model}"

  sem_slurm="${sem_levels//,/-}"
  export_vars="ALL,MODEL=${model},STRUCTURAL_LEVELS=1,SEMANTIC_LEVELS=${sem_slurm}"
  if [[ "$load_8bit" == "1" ]]; then
    export_vars="${export_vars},LOCAL_LOAD_IN_8BIT=1"
  else
    export_vars="${export_vars},LOCAL_LOAD_IN_8BIT=0"
  fi

  cmd=(
    sbatch
    "${SBATCH_EXTRA[@]}"
    --job-name="${job_name}"
    --gres="gpu:${gpus}"
    --mem="${mem}G"
    --time="${walltime}"
    --output="${LOG_DIR}/${job_name}_%j.out"
    --error="${LOG_DIR}/${job_name}_%j.err"
    --export="${export_vars}"
    "${SCRIPT_DIR}/run_rerun_model.sbatch"
  )

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] ${cmd[*]}"
  else
    echo "Submitting ${model} L1S${sem_levels} (${gpus} GPU, ${mem}G, 8bit=${load_8bit})"
    if "${cmd[@]}"; then
      SUBMITTED=$((SUBMITTED + 1))
    else
      echo "ERROR: sbatch failed for ${model}" >&2
      FAILED=$((FAILED + 1))
    fi
  fi
done

echo
if [[ "$DRY_RUN" == "1" ]]; then
  echo "Dry run only - no jobs submitted."
else
  echo "Submitted ${SUBMITTED}/${#SPECS[@]} jobs."
  if [[ "$FAILED" -gt 0 ]]; then
    exit 1
  fi
  echo "Monitor: squeue -u \$USER"
fi
