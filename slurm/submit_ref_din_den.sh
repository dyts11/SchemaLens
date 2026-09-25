#!/usr/bin/env bash
# Submit reflexion + dense + din experiments for qwen2.5-coder-14b-local.
# Jobs are submitted to both weics and data-inst partitions simultaneously;
# each job starts on whichever node (k176 or k179) becomes free first.
#
# Usage (from schema_effect/):
#   bash slurm/submit_ref_din_den.sh
#   DRY_RUN=1 bash slurm/submit_ref_din_den.sh   # preview only

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

# Both partitions — SLURM starts the job on whichever is free first.
WEICS_PART="${SLURM_WEICS_PARTITION:-weics}"
DATA_INST_PART="${SLURM_DATA_INST_PARTITION:-data-inst}"
PARTITION="${WEICS_PART},${DATA_INST_PART}"

LOG_DIR="${SCHEMA_EFFECT_ROOT}/slurm/logs"
mkdir -p "$LOG_DIR"

SBATCH_BASE=(
  --partition="${PARTITION}"
  --gres=gpu:1
  --mem=128G
  --cpus-per-task=8
)
if [[ -n "${SLURM_ACCOUNT:-}" ]]; then
  SBATCH_BASE+=(--account="${SLURM_ACCOUNT}")
fi

# experiment name | sbatch file | job name
EXPERIMENTS=(
  "reflexion|${SCRIPT_DIR}/run_reflexion_qwen14b.sbatch|reflexion-qwen14b"
  "dense|${SCRIPT_DIR}/run_dense_qwen14b.sbatch|dense-qwen14b"
  "din|${SCRIPT_DIR}/run_din_qwen14b.sbatch|din-qwen14b"
)

echo "Partition : ${PARTITION}  (first available node wins)"
echo "Account   : ${SLURM_ACCOUNT:-<default>}"
echo "Walltime  : 72:00:00"
echo "Experiments: reflexion, dense, din  (qwen2.5-coder-14b-local; dense: L3-L6 x S1-S3)"
echo

SUBMITTED=0
FAILED=0

for spec in "${EXPERIMENTS[@]}"; do
  IFS='|' read -r exp_name sbatch_file job_name <<< "$spec"

  cmd=(
    sbatch
    "${SBATCH_BASE[@]}"
    --job-name="${job_name}"
    --time=72:00:00
    --output="${LOG_DIR}/${job_name}_%j.out"
    --error="${LOG_DIR}/${job_name}_%j.err"
    "${sbatch_file}"
  )

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] ${cmd[*]}"
  else
    echo "Submitting ${exp_name} -> ${PARTITION} ..."
    if "${cmd[@]}"; then
      SUBMITTED=$((SUBMITTED + 1))
    else
      echo "ERROR: sbatch failed for ${exp_name}" >&2
      FAILED=$((FAILED + 1))
    fi
  fi
done

echo
if [[ "$DRY_RUN" == "1" ]]; then
  echo "Dry run complete — no jobs submitted."
  echo "To submit: bash slurm/submit_ref_din_den.sh"
else
  echo "Submitted ${SUBMITTED}/3 jobs to ${PARTITION}."
  [[ "$FAILED" -gt 0 ]] && exit 1
  echo "Monitor : squeue -u \$USER"
  echo "Logs    : ${LOG_DIR}/reflexion-qwen14b_*.out  dense-qwen14b_*.out  din-qwen14b_*.out"
  echo "Results : ${SCHEMA_EFFECT_ROOT}/results/{reflexion,dense,din}/"
fi
