#!/usr/bin/env bash
# Submit Spider experiment (car_1 + tvshow, 154 Q, 18 conditions) on weics (H100).
#
# One SLURM job per model (8 jobs total). Each job runs L1�L6 x S1�S3 via
# run_experiment.py (conditions are not passed through sbatch --export).
#
# Usage:
#   cd /group/pmc050/dsu/schema_effect
#   DRY_RUN=1 bash slurm/submit_spider.sh
#   bash slurm/submit_spider.sh
#
# Optional in slurm/config.env:
#   export SLURM_WEICS_PARTITION="weics"
#   export SLURM_WEICS_NODELIST="k176"
#
# Output: results/spider/<model>__L<sl>S<sem>.csv  (18 CSVs per model)

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

WEICS_PARTITION="${SLURM_WEICS_PARTITION:-weics}"

# model_key | gpus | mem_gb | walltime | load_8bit (0=fp16 on H100, 1=8bit)
SPECS=(
  #"qwen2.5-coder-0.5b-local|1|32|24:00:00|0"
  #"qwen2.5-coder-1.5b-local|1|32|24:00:00|0"
  #"qwen2.5-coder-3b-local|1|48|36:00:00|0"
 # "qwen2.5-coder-7b-local|1|64|48:00:00|0"
  #"qwen2.5-coder-14b-local|1|128|72:00:00|0"
  #"phi-4-local|1|128|72:00:00|0"
  #"olmo-2-13b-local|1|128|72:00:00|0"
  "qwen2.5-coder-32b-local|1|128|72:00:00|0"
)

echo "Host: $(hostname)"
echo "Partition=${WEICS_PARTITION} (H100)"
echo "Spider: 154 questions x 18 conditions x ${#SPECS[@]} models"
echo "Output: ${SCHEMA_EFFECT_ROOT}/results/spider/"
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
  job_name="spider-${model}"

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
    "${SCRIPT_DIR}/run_spider_experiment.sbatch"
  )

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] ${cmd[*]}"
  else
    echo "Submitting ${model} -> ${WEICS_PARTITION} (${gpus} GPU, ${mem}G, ${walltime}, 8bit=${load_8bit})"
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
  echo "Logs: ${LOG_DIR}/spider-*"
  echo "Results: ${SCHEMA_EFFECT_ROOT}/results/spider/<model>__L*S*.csv"
fi
