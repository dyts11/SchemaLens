#!/usr/bin/env bash
# Submit 8 GPU rerun jobs (one per model). Run inside an salloc shell.
#
# Step 1 - from login node, allocate a work node:
#   salloc -p work --cpus-per-task=1 --mem=4G --time=00:30:00
#
# Step 2 - once the shell prompt changes (you are on a compute node):
#   cd /group/pmc050/dsu/schema_effect
#   bash slurm/submit_rerun_european_football_2.sh
#   exit
#
# Step 3 - monitor from login node:
#   squeue -u $USER
#
# Preview without submitting:
#   DRY_RUN=1 bash slurm/submit_rerun_european_football_2.sh

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

# model_key | gpus | mem_gb | walltime
SPECS=(
  "qwen2.5-coder-0.5b-local|1|32|08:00:00"
  "qwen2.5-coder-1.5b-local|1|32|08:00:00"
  "qwen2.5-coder-3b-local|1|32|10:00:00"
  "qwen2.5-coder-7b-local|1|48|12:00:00"
  "qwen2.5-coder-14b-local|1|64|16:00:00"
  "phi-4-local|1|64|16:00:00"
  "olmo-2-13b-local|1|64|16:00:00"
  "qwen2.5-coder-32b-local|2|128|24:00:00"
)

GPU_PARTITION="${SLURM_PARTITION:-gpu}"

echo "Host: $(hostname)"
echo "RERUN_DB_ID=${RERUN_DB_ID}"
echo "SCHEMA_EFFECT_ROOT=${SCHEMA_EFFECT_ROOT}"
echo "LOCAL_MODELS_DIR=${LOCAL_MODELS_DIR}"
echo "GPU partition=${GPU_PARTITION}"
echo "SLURM_ACCOUNT=${SLURM_ACCOUNT:-<not set>}"
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
  IFS='|' read -r model gpus mem walltime <<< "$spec"
  job_name="rerun-${RERUN_DB_ID}-${model}"

  cmd=(
    sbatch
    "${SBATCH_EXTRA[@]}"
    --job-name="${job_name}"
    --gres="gpu:${gpus}"
    --mem="${mem}G"
    --time="${walltime}"
    --output="${LOG_DIR}/${job_name}_%j.out"
    --error="${LOG_DIR}/${job_name}_%j.err"
    --export="ALL,MODEL=${model}"
    "${SCRIPT_DIR}/run_rerun_model.sbatch"
  )

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] ${cmd[*]}"
  else
    echo "Submitting ${model} (${gpus} GPU, ${mem}G, ${walltime})"
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
  echo "Submitted ${SUBMITTED}/${#SPECS[@]} GPU jobs to partition ${GPU_PARTITION}."
  if [[ "$FAILED" -gt 0 ]]; then
    echo "FAILED ${FAILED} submissions. Check:" >&2
    echo "  sacctmgr show assoc user=\$USER" >&2
    echo "  slurm/config.env (SLURM_ACCOUNT, SLURM_PARTITION)" >&2
    exit 1
  fi
  echo "Monitor: squeue -u \$USER"
  echo "Logs: ${LOG_DIR}/"
  echo "Results: ${SCHEMA_EFFECT_ROOT}/results/rerun/${RERUN_DB_ID}__<model>__L1S*.csv"
fi
