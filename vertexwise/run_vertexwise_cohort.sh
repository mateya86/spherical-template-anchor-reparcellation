#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 3 ]] || { echo "Usage: $0 SUBJECTS_DIR COHORT_CSV OUTPUT_DIR" >&2; exit 1; }
SUBJECTS_DIR_INPUT="$1"; COHORT="$2"; OUTPUT="$3"; SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
tail -n +2 "$COHORT" | while IFS=, read -r subject hemi; do
  [[ -n "$subject" && -n "$hemi" ]] || continue
  python3 "$SCRIPT_DIR/star_vertexwise_analysis.py" --subjects-dir "$SUBJECTS_DIR_INPUT" --subject "$subject" --hemi "$hemi" --output-dir "$OUTPUT"
done
