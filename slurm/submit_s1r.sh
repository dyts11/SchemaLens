#!/usr/bin/env bash
# Submit BIRD S1R (randomised alias) experiment on weics (H100).
#
# One SLURM job per model (8 jobs total).
# Conditions: L1-L6 x S1R (6 conditions, hardcoded in run_experiment_s1r.py).
# Questions: ~397 per condition (arcwise minus card_games + codebase_community).
# Output: results_s1r/<model>__L<sl>S1R.csv
#
# Usage:
#   cd /group/pmc050/dsu/schema_effect
#   DRY_RUN=1 bash slurm/submit_s1r.sh          # preview sbatch commands
#   bash slurm/submit_s1r.sh                     # submit all 8 jobs
#   bash slurm/submit_s1r.sh qwen2.5-coder-14b-local   # single model

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${SCRIPT_DIR}/config.env"
DRY_RUN="${DRY_RUN:-0}"
FILTER_MODEL="${1:-}"
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

# model_key | gpus | mem_gb | walltime | load_8bit
SPECS=(
  "qwen2.5-coder-0.5b-local|1|32|72:00:00|0"
  "qwen2.5-coder-1.5b-local|1|32|72:00:00|0"
  "qwen2.5-coder-3b-local|1|48|72:00:00|0"
  "qwen2.5-coder-7b-local|1|64|72:00:00|0"
  "qwen2.5-coder-14b-local|1|128|72:00:00|0"
  "qwen2.5-coder-32b-local|1|128|72:00:00|0"
  "phi-4-local|1|128|72:00:00|0"
  "olmo-2-13b-local|1|128|72:00:00|0"
)

echo "Host: $(hostname)"
echo "Partition=${WEICS_PARTITION} (H100)"
echo "S1R: ~397 questions x 6 conditions x ${#SPECS[@]} models"
echo "Output: ${SCHEMA_EFFECT_ROOT}/results_s1r/"
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

  if [[ -n "$FILTER_MODEL" && "$model" != "$FILTER_MODEL" ]]; then
    continue
  fi

  job_name="s1r-${model}"

  export_vars="ALL,MODEL=${model},LOCAL_LOAD_IN_8BIT=${load_8bit}"

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
    "${SCRIPT_DIR}/run_s1r_experiment.sbatch"
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
  echo "Dry run complete — no jobs submitted."
  echo "To submit: bash slurm/submit_s1r.sh"
else
  echo "Submitted ${SUBMITTED}/${#SPECS[@]} jobs to ${WEICS_PARTITION}."
  if [[ "$FAILED" -gt 0 ]]; then
    exit 1
  fi
  echo "Monitor : squeue -u \$USER -p ${WEICS_PARTITION}"
  echo "Logs    : ${LOG_DIR}/s1r-*"
  echo "Results : ${SCHEMA_EFFECT_ROOT}/results_s1r/<model>__L*S1R.csv"
fi
