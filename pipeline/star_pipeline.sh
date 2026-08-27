#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  star_pipeline.sh \
    --subject SUBJECT_ID \
    --subjects-dir SUBJECTS_DIR \
    --results-dir RESULTS_DIR
EOF
}

SUBJECT=""
SUBJECTS_DIR_INPUT=""
RESULTS_DIR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --subject)
            SUBJECT="${2:-}"
            shift 2
            ;;
        --subjects-dir)
            SUBJECTS_DIR_INPUT="${2:-}"
            shift 2
            ;;
        --results-dir)
            RESULTS_DIR="${2:-}"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Error: Unknown argument: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

[[ -n "$SUBJECT" ]] || { echo "Error: --subject is required." >&2; usage >&2; exit 1; }
[[ -n "$SUBJECTS_DIR_INPUT" ]] || { echo "Error: --subjects-dir is required." >&2; usage >&2; exit 1; }
[[ -n "$RESULTS_DIR" ]] || { echo "Error: --results-dir is required." >&2; usage >&2; exit 1; }
[[ -n "${FREESURFER_HOME:-}" ]] || {
    echo "Error: FREESURFER_HOME is not defined. Source FreeSurfer first." >&2
    exit 1
}

export SUBJECTS_DIR="$SUBJECTS_DIR_INPUT"
SUBJECT_DIR="${SUBJECTS_DIR}/${SUBJECT}"
SURF_DIR="${SUBJECT_DIR}/surf"
LABEL_DIR="${SUBJECT_DIR}/label"
STATS_DIR="${SUBJECT_DIR}/stats"

[[ -d "$SUBJECT_DIR" ]] || { echo "Error: Subject directory not found: $SUBJECT_DIR" >&2; exit 1; }

required_files=(
    "${SURF_DIR}/lh.sphere"
    "${SURF_DIR}/rh.sphere"
    "${SURF_DIR}/lh.sphere.reg"
    "${SURF_DIR}/rh.sphere.reg"
    "${SURF_DIR}/lh.white"
    "${SURF_DIR}/rh.white"
    "${LABEL_DIR}/lh.cortex.label"
    "${LABEL_DIR}/rh.cortex.label"
)
for required_file in "${required_files[@]}"; do
    [[ -f "$required_file" ]] || { echo "Error: Required file not found: $required_file" >&2; exit 1; }
done

mkdir -p "$RESULTS_DIR"
cd "$SUBJECT_DIR"

# Back up the native registrations.
cp "${SURF_DIR}/lh.sphere.reg" "${SURF_DIR}/lh.sphere.reg.backup"
cp "${SURF_DIR}/rh.sphere.reg" "${SURF_DIR}/rh.sphere.reg.backup"

# Re-register using the Buckner40 templates.
mris_register \
    "${SURF_DIR}/lh.sphere" \
    "${FREESURFER_HOME}/average/lh.average.curvature.filled.buckner40.tif" \
    "${SURF_DIR}/lh.sphere.reg"

mris_register \
    "${SURF_DIR}/rh.sphere" \
    "${FREESURFER_HOME}/average/rh.average.curvature.filled.buckner40.tif" \
    "${SURF_DIR}/rh.sphere.reg"

# Re-parcellate.
mris_ca_label \
    "$SUBJECT" lh \
    "${SURF_DIR}/lh.sphere.reg" \
    "${FREESURFER_HOME}/average/lh.curvature.buckner40.filled.desikan_killiany.2010-03-25.gcs" \
    "${LABEL_DIR}/lh.aparc.annot"

mris_ca_label \
    "$SUBJECT" rh \
    "${SURF_DIR}/rh.sphere.reg" \
    "${FREESURFER_HOME}/average/rh.curvature.buckner40.filled.desikan_killiany.2010-03-25.gcs" \
    "${LABEL_DIR}/rh.aparc.annot"

# Refresh annotation-derived statistics.
mris_anatomical_stats \
    -mgz -cortex "${LABEL_DIR}/lh.cortex.label" \
    -f "${STATS_DIR}/lh.aparc.stats" -b \
    -a "${LABEL_DIR}/lh.aparc.annot" \
    "$SUBJECT" lh white

mris_anatomical_stats \
    -mgz -cortex "${LABEL_DIR}/rh.cortex.label" \
    -f "${STATS_DIR}/rh.aparc.stats" -b \
    -a "${LABEL_DIR}/rh.aparc.annot" \
    "$SUBJECT" rh white

# Extract regional tables.
aparcstats2table --subjects "$SUBJECT" --hemi lh --meas volume --tablefile "${RESULTS_DIR}/lh_volume.txt"
aparcstats2table --subjects "$SUBJECT" --hemi rh --meas volume --tablefile "${RESULTS_DIR}/rh_volume.txt"
aparcstats2table --subjects "$SUBJECT" --hemi lh --meas thickness --tablefile "${RESULTS_DIR}/lh_thickness.txt"
aparcstats2table --subjects "$SUBJECT" --hemi rh --meas thickness --tablefile "${RESULTS_DIR}/rh_thickness.txt"
aparcstats2table --subjects "$SUBJECT" --hemi lh --meas area --tablefile "${RESULTS_DIR}/lh_area.txt"
aparcstats2table --subjects "$SUBJECT" --hemi rh --meas area --tablefile "${RESULTS_DIR}/rh_area.txt"
asegstats2table --subjects "$SUBJECT" --meas volume --tablefile "${RESULTS_DIR}/aseg_volume.txt"

echo "STAR pipeline finished. Files saved to: $RESULTS_DIR"
