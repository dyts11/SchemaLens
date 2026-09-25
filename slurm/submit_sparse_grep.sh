#!/usr/bin/env bash
# Submit sparse (BM25) + grep (word-overlap) retrieval experiments for qwen2.5-coder-14b-local.
# Jobs run on the ondemand-gpu partition (12h wall time limit).
#
# Usage (from schema_effect/):
#   bash slurm/submit_sparse_grep.sh
#   DRY_RUN=1 bash slurm/submit_sparse_grep.sh   # preview only

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

PARTITION="${SLURM_ONDEMAND_PARTITION:-ondemand-gpu}"
WALLTIME="12:00:00"

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
  "sparse|${SCRIPT_DIR}/run_sparse_qwen14b.sbatch|sparse-qwen14b"
  "grep|${SCRIPT_DIR}/run_grep_qwen14b.sbatch|grep-qwen14b"
)

echo "Partition : ${PARTITION}"
echo "Account   : ${SLURM_ACCOUNT:-<default>}"
echo "Walltime  : ${WALLTIME}"
echo "Experiments: sparse, grep  (qwen2.5-coder-14b-local; L3-L6 x S1-S3)"
echo

SUBMITTED=0
FAILED=0

for spec in "${EXPERIMENTS[@]}"; do
  IFS='|' read -r exp_name sbatch_file job_name <<< "$spec"

  cmd=(
    sbatch
    "${SBATCH_BASE[@]}"
    --job-name="${job_name}"
    --time="${WALLTIME}"
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
  echo "To submit: bash slurm/submit_sparse_grep.sh"
else
  echo "Submitted ${SUBMITTED}/2 jobs to ${PARTITION}."
  [[ "$FAILED" -gt 0 ]] && exit 1
  echo "Monitor : squeue -u \$USER"
  echo "Logs    : ${LOG_DIR}/sparse-qwen14b_*.out  grep-qwen14b_*.out"
  echo "Results : ${SCHEMA_EFFECT_ROOT}/results/{sparse,grep}/"
fi
