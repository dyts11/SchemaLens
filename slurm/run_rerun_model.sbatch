#!/bin/bash
# GPU worker: runs rerun_db_experiment for one model.
# Submitted by submit_rerun_european_football_2.sh
#
# Note: SLURM copies this script to /var/spool/slurmd/... - do not resolve
# paths from BASH_SOURCE; use SCHEMA_EFFECT_ROOT from the environment.

#SBATCH --cpus-per-task=8

set -euo pipefail

# Exported by submit script via --export=ALL (after sourcing config.env)
SCHEMA_EFFECT_ROOT="${SCHEMA_EFFECT_ROOT:-/group/pmc050/dsu/schema_effect}"
CONFIG="${SCHEMA_EFFECT_ROOT}/slurm/config.env"

if [[ ! -f "$CONFIG" ]]; then
  echo "Missing ${CONFIG}" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$CONFIG"

if [[ -z "${MODEL:-}" ]]; then
  echo "MODEL env var is required (set by submit script)" >&2
  exit 1
fi

export LOCAL_MODELS_DIR
export HF_HOME="${HF_HOME:-${LOCAL_MODELS_DIR}/.cache}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

source "${VENV_DIR}/bin/activate"
cd "${SCHEMA_EFFECT_ROOT}"

echo "Host: $(hostname)"
echo "Date: $(date -Is)"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-}"
echo "MODEL=${MODEL}"
echo "RERUN_DB_ID=${RERUN_DB_ID}"
echo "SCHEMA_EFFECT_ROOT=${SCHEMA_EFFECT_ROOT}"
echo "LOCAL_MODELS_DIR=${LOCAL_MODELS_DIR}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}"
nvidia-smi || true
echo

python -m src.rerun_db_experiment "${RERUN_DB_ID}" --models "${MODEL}"

echo
echo "Finished ${MODEL} at $(date -Is)"
