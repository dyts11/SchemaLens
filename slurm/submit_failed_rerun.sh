#!/usr/bin/env bash
# Submit remaining european_football_2 reruns on weics (H100).
#
# Semantic levels are hardcoded in slurm/run_rerun_model.sbatch (not via --export).
#   olmo-2-13b-local      -> L1S2, L1S3
#   qwen2.5-coder-32b-local -> L1S2, L1S3
#   qwen2.5-coder-7b-local  -> L1S3
#
# Usage:
#   cd /group/pmc050/dsu/schema_effect
#   DRY_RUN=1 bash slurm/submit_failed_rerun.sh
#   bash slurm/submit_failed_rerun.sh

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

# model | gpus | mem_gb | walltime | load_8bit
SPECS=(
  "olmo-2-13b-local|1|128|12:00:00|0"
  "qwen2.5-coder-32b-local|1|128|16:00:00|0"
  "qwen2.5-coder-7b-local|1|64|08:00:00|0"
)

WEICS_PARTITION="${SLURM_WEICS_PARTITION:-weics}"

echo "Host: $(hostname)"
echo "RERUN_DB_ID=${RERUN_DB_ID}"
echo "Partition=${WEICS_PARTITION} (H100)"
echo "3 jobs: olmo+32B (L1S2,S3), 7B (L1S3) — levels in run_rerun_model.sbatch"
echo

SBATCH_EXTRA=()
if [[ -n "${SLURM_ACCOUNT:-}" ]]; then
  SBATCH_EXTRA+=(--account="${SLURM_ACCOUNT}")
fi
SBATCH_EXTRA+=(--partition="${WEICS_PARTITION}")
if [[ -n "${SLURM_QOS:-}" ]]; then
  SBATCH_EXTRA+=(--qos="${SLURM_QOS}")
fi
if [[ -n "${SLURM_WEICS_NODELIST:-}" ]]; then
  SBATCH_EXTRA+=(--nodelist="${SLURM_WEICS_NODELIST}")
fi

for spec in "${SPECS[@]}"; do
  IFS='|' read -r model gpus mem walltime load_8bit <<< "$spec"
  job_name="${RERUN_DB_ID}-${model}"

  export_vars="ALL,MODEL=${model}"
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
    echo "Submitting ${model} -> ${WEICS_PARTITION} (${gpus} GPU, 8bit=${load_8bit})"
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
  echo "Submitted ${SUBMITTED}/${#SPECS[@]} jobs to ${WEICS_PARTITION}."
  if [[ "$FAILED" -gt 0 ]]; then
    exit 1
  fi
  echo "Monitor: squeue -u \$USER -p ${WEICS_PARTITION}"
fi
