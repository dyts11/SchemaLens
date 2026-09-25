#!/usr/bin/env bash
# Submit BIRD 3-shot few-shot experiment on weics (H100).
#
# One SLURM job per model (8 jobs total).
# Conditions: L1-L2 x S1-S3 + L4-L6 x S1-S3 (15 conditions, hardcoded in run_experiment.py).
# Questions: 465 per condition (498 arcwise minus 33 reserved as examples).
# Output: results/fewshot/<model>__L<sl>S<sem>__fs3.csv
#
# Usage:
#   cd /group/pmc050/dsu/schema_effect
#   DRY_RUN=1 bash slurm/submit_fewshot.sh        # preview sbatch commands
#   bash slurm/submit_fewshot.sh                   # submit all 8 jobs
#   bash slurm/submit_fewshot.sh qwen2.5-coder-14b-local   # single model
#
# Optional in slurm/config.env:
#   export SLURM_WEICS_PARTITION="weics"
#   export SLURM_WEICS_NODELIST="k176"

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${SCRIPT_DIR}/config.env"
DRY_RUN="${DRY_RUN:-0}"
FILTER_MODEL="${1:-}"        # optional: submit only this model key
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
# Walltime budget: 465 Q x 15 conditions = 6 975 prompts per model.
# Checkpointing is built in — safe to resubmit if a job times out.
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
echo "Few-shot: 3-shot fixed per DB (simple + moderate + challenging)"
echo "BIRD: 465 questions x 15 conditions x ${#SPECS[@]} models"
echo "Output: ${SCHEMA_EFFECT_ROOT}/results/fewshot/"
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

  # Skip if a filter was given and this model doesn't match
  if [[ -n "$FILTER_MODEL" && "$model" != "$FILTER_MODEL" ]]; then
    continue
  fi

  job_name="fewshot-${model}"

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
    "${SCRIPT_DIR}/run_fewshot_experiment.sbatch"
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
  echo "To submit: bash slurm/submit_fewshot.sh"
else
  echo "Submitted ${SUBMITTED}/${#SPECS[@]} jobs to ${WEICS_PARTITION}."
  if [[ "$FAILED" -gt 0 ]]; then
    exit 1
  fi
  echo "Monitor : squeue -u \$USER -p ${WEICS_PARTITION}"
  echo "Logs    : ${LOG_DIR}/fewshot-*"
  echo "Results : ${SCHEMA_EFFECT_ROOT}/results/fewshot/<model>__L*S*__fs3.csv"
fi
