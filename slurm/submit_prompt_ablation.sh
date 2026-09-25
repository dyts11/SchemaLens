#!/usr/bin/env bash
# Submit prompt ablation experiment: qwen2.5-coder-14b-local, BIRD, all 15 conditions.
#
# Submits 6 jobs: 3 variants x 2 condition groups.
#
#   Variant     Conditions          Results dir
#   cot         L1-L2 x S1-S3      results/cot/
#   cot         L3-L6 x S1-S3      results/cot/
#   ev          L1-L2 x S1-S3      results/ev/
#   ev          L3-L6 x S1-S3      results/ev/
#   cot_ev      L1-L2 x S1-S3      results/cot_ev/
#   cot_ev      L3-L6 x S1-S3      results/cot_ev/
#
# Usage:
#   cd /group/pmc050/dsu/schema_effect
#   DRY_RUN=1 bash slurm/submit_prompt_ablation.sh          # preview
#   bash slurm/submit_prompt_ablation.sh                     # submit all 6
#   bash slurm/submit_prompt_ablation.sh cot                 # submit cot variant only
#
# Optional overrides via slurm/config.env:
#   export SLURM_PARTITION="gpu"
#   export SLURM_ACCOUNT="pmc050"

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${SCRIPT_DIR}/config.env"
DRY_RUN="${DRY_RUN:-0}"
FILTER_VARIANT="${1:-}"   # optional: submit only this variant (cot|ev|cot_ev)
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

WEICS_PART="${SLURM_WEICS_PARTITION:-weics}"
DATA_INST_PART="${SLURM_DATA_INST_PARTITION:-data-inst}"
PARTITION="${WEICS_PART},${DATA_INST_PART}"

# variant | condition_group | gpus | mem_gb | walltime
# Timing estimate at ~20 s/question x 498 questions:
#   l1l2     (6 conditions):  ~16 h  → well inside 72 h
#   l3l4l5l6 (12 conditions): ~33 h  → well inside 72 h
JOBS=(
  "cot|l1l2|1|128|72:00:00"
  "cot|l3l4l5l6|1|128|72:00:00"
  "ev|l1l2|1|128|72:00:00"
  "ev|l3l4l5l6|1|128|72:00:00"
  "cot_ev|l1l2|1|128|72:00:00"
  "cot_ev|l3l4l5l6|1|128|72:00:00"
)

echo "Host: $(hostname)"
echo "Partition : ${PARTITION}  (first available node wins)"
echo "Model: qwen2.5-coder-14b-local"
echo "Variants: cot | ev | cot_ev"
echo "Condition groups: l1l2 (6 cond.) | l3l4l5l6 (12 cond.)"
echo "Total jobs: ${#JOBS[@]}"
echo "Results:"
echo "  ${SCHEMA_EFFECT_ROOT}/results/cot/"
echo "  ${SCHEMA_EFFECT_ROOT}/results/ev/"
echo "  ${SCHEMA_EFFECT_ROOT}/results/cot_ev/"
echo

SBATCH_EXTRA=()
if [[ -n "${SLURM_ACCOUNT:-}" ]]; then
  SBATCH_EXTRA+=(--account="${SLURM_ACCOUNT}")
fi
SBATCH_EXTRA+=(--partition="${PARTITION}")
if [[ -n "${SLURM_QOS:-}" ]]; then
  SBATCH_EXTRA+=(--qos="${SLURM_QOS}")
fi

for job_spec in "${JOBS[@]}"; do
  IFS='|' read -r variant cond_group gpus mem walltime <<< "$job_spec"

  if [[ -n "$FILTER_VARIANT" && "$variant" != "$FILTER_VARIANT" ]]; then
    continue
  fi

  job_name="ablation-${variant}-${cond_group}"
  export_vars="ALL,VARIANT=${variant},CONDITION_GROUP=${cond_group},LOCAL_LOAD_IN_8BIT=0"

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
    "${SCRIPT_DIR}/run_prompt_ablation_qwen14b.sbatch"
  )

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] ${cmd[*]}"
  else
    echo "Submitting ${variant} / ${cond_group} → ${PARTITION} (${gpus} GPU, ${mem}G, ${walltime})"
    if "${cmd[@]}"; then
      SUBMITTED=$((SUBMITTED + 1))
    else
      echo "ERROR: sbatch failed for ${variant}/${cond_group}" >&2
      FAILED=$((FAILED + 1))
    fi
  fi
done

echo
if [[ "$DRY_RUN" == "1" ]]; then
  echo "Dry run complete — no jobs submitted."
  echo "To submit: bash slurm/submit_prompt_ablation.sh"
else
  echo "Submitted ${SUBMITTED} job(s)."
  if [[ "$FAILED" -gt 0 ]]; then
    exit 1
  fi
  echo "Monitor : squeue -u \$USER -p ${WEICS_PART},${DATA_INST_PART}"
  echo "Logs    : ${LOG_DIR}/ablation-*"
  echo "Results : ${SCHEMA_EFFECT_ROOT}/results/{cot,ev,cot_ev}/"
fi
