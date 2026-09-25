#!/usr/bin/env bash
# Submit L1/L2 no-denorm-notice ablation on weics (H100).
#
# 1 model (Qwen 14B), 6 conditions (L1S1-S3 + L2S1-S3), 397 questions each.
# Conditions live in src/run_without_denorm_notice_experiment.py (safe from SLURM --export comma bug).
# Output: results/without_denorm_notice/qwen2.5-coder-14b-local__L*S*.csv
#
# Usage:
#   cd /group/pmc050/dsu/schema_effect
#   DRY_RUN=1 bash slurm/submit_without_denorm_notice.sh
#   bash slurm/submit_without_denorm_notice.sh
#
# Optional in slurm/config.env:
#   export SLURM_WEICS_PARTITION="weics"
#   export SLURM_WEICS_NODELIST="k176"

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${SCRIPT_DIR}/config.env"
DRY_RUN="${DRY_RUN:-0}"

if [[ ! -f "$CONFIG" ]]; then
  echo "Missing ${CONFIG}. Copy slurm/config.env.example to slurm/config.env." >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$CONFIG"

LOG_DIR="${SCHEMA_EFFECT_ROOT}/slurm/logs"
mkdir -p "$LOG_DIR"

WEICS_PARTITION="${SLURM_WEICS_PARTITION:-weics}"
JOB_NAME="no-denorm-notice-qwen14b"
GPUS=1
MEM_GB=128
WALLTIME="48:00:00"

echo "Host: $(hostname)"
echo "Partition=${WEICS_PARTITION} (H100)"
echo "Job: Qwen 14B, L1+L2 x S1-S3, no denorm notice, 397 questions"
echo "Output: ${SCHEMA_EFFECT_ROOT}/results/without_denorm_notice/"
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

export_vars="ALL,LOCAL_LOAD_IN_8BIT=0"

cmd=(
  sbatch
  "${SBATCH_EXTRA[@]}"
  --job-name="${JOB_NAME}"
  --gres="gpu:${GPUS}"
  --mem="${MEM_GB}G"
  --time="${WALLTIME}"
  --output="${LOG_DIR}/${JOB_NAME}_%j.out"
  --error="${LOG_DIR}/${JOB_NAME}_%j.err"
  --export="${export_vars}"
  "${SCRIPT_DIR}/run_without_denorm_notice.sbatch"
)

if [[ "$DRY_RUN" == "1" ]]; then
  echo "[dry-run] ${cmd[*]}"
  echo
  echo "Local preview: python -m src.run_without_denorm_notice_experiment --dry-run"
else
  echo "Submitting -> ${WEICS_PARTITION} (${GPUS} GPU, ${MEM_GB}G, ${WALLTIME})"
  "${cmd[@]}"
  echo
  echo "Monitor: squeue -u \$USER -p ${WEICS_PARTITION}"
  echo "Logs: ${LOG_DIR}/${JOB_NAME}_*.out"
fi
