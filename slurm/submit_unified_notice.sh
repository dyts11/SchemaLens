#!/usr/bin/env bash
# Submit the unified-notice experiment: qwen2.5-coder-14b-local, BIRD, all 18 conditions,
# identical prompt template (Deduplication Rules notice) on every condition.
#
# Submits 1 job (1 GPU, 72 h, weics partition / H100 k176) running all 18
# conditions sequentially → results/unified_notice/
#
# The matching no-notice grid already exists for qwen14b and need not be rerun:
#   L1/L2 → results/without_denorm_notice/   L3-L6 → results/full/
# (both used the plain template). To regenerate it anyway: NO_NOTICE=1 bash slurm/submit_unified_notice.sh
#
# Usage:
#   cd /group/pmc050/dsu/schema_effect
#   DRY_RUN=1 bash slurm/submit_unified_notice.sh      # preview
#   bash slurm/submit_unified_notice.sh                # submit

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${SCRIPT_DIR}/config.env"
DRY_RUN="${DRY_RUN:-0}"
NO_NOTICE="${NO_NOTICE:-0}"
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

PARTITION="${SLURM_WEICS_PARTITION:-weics}"

TAG=$([[ "$NO_NOTICE" == "1" ]] && echo "nonotice" || echo "notice")
RESULTS_SUBDIR=$([[ "$NO_NOTICE" == "1" ]] && echo "no_notice" || echo "unified_notice")

GPUS=1
MEM_GB=128
WALLTIME="72:00:00"   # 18 conditions x 397 questions at ~20 s/question ≈ 40 h

echo "Host: $(hostname)"
echo "Partition : ${PARTITION}"
echo "Model     : qwen2.5-coder-14b-local"
echo "Notice    : ${TAG}"
echo "Results   : ${SCHEMA_EFFECT_ROOT}/results/${RESULTS_SUBDIR}/"
echo

SBATCH_EXTRA=()
if [[ -n "${SLURM_ACCOUNT:-}" ]]; then
  SBATCH_EXTRA+=(--account="${SLURM_ACCOUNT}")
fi
SBATCH_EXTRA+=(--partition="${PARTITION}")
if [[ -n "${SLURM_QOS:-}" ]]; then
  SBATCH_EXTRA+=(--qos="${SLURM_QOS}")
fi

job_name="unified-${TAG}"
export_vars="ALL,NO_NOTICE=${NO_NOTICE},LOCAL_LOAD_IN_8BIT=0"

cmd=(
  sbatch
  "${SBATCH_EXTRA[@]}"
  --job-name="${job_name}"
  --gres="gpu:${GPUS}"
  --mem="${MEM_GB}G"
  --time="${WALLTIME}"
  --output="${LOG_DIR}/${job_name}_%j.out"
  --error="${LOG_DIR}/${job_name}_%j.err"
  --export="${export_vars}"
  "${SCRIPT_DIR}/run_unified_notice_qwen14b.sbatch"
)

if [[ "$DRY_RUN" == "1" ]]; then
  echo "[dry-run] ${cmd[*]}"
else
  echo "Submitting ${job_name} → ${PARTITION} (${GPUS} GPU, ${MEM_GB}G, ${WALLTIME})"
  if "${cmd[@]}"; then
    SUBMITTED=$((SUBMITTED + 1))
  else
    echo "ERROR: sbatch failed" >&2
    FAILED=$((FAILED + 1))
  fi
fi

echo
if [[ "$DRY_RUN" == "1" ]]; then
  echo "Dry run complete — no jobs submitted."
else
  echo "Submitted ${SUBMITTED} job(s)."
  [[ "$FAILED" -gt 0 ]] && exit 1
  echo "Monitor : squeue -u \$USER -p ${PARTITION}"
  echo "Logs    : ${LOG_DIR}/unified-${TAG}-*"
  echo "Results : ${SCHEMA_EFFECT_ROOT}/results/${RESULTS_SUBDIR}/"
fi
