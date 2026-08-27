# STAR Reparcellation Software

This repository includes:

- `pipeline/star_pipeline.sh`: STAR spherical re-registration, cortical reparcellation, statistics refresh, and table extraction.
- `validation/star_cross_validator.py`: cross-sectional and longitudinal volumetric validation.
- `vertexwise/star_vertexwise_analysis.py`: native-versus-STAR spherical-coordinate displacement analysis.
- `vertexwise/create_star_heatmaps.py`: binned displacement annotation generation.

## Install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run STAR

```bash
bash pipeline/star_pipeline.sh \
  --subject SUBJECT_ID \
  --subjects-dir /path/to/freesurfer-subjects \
  --results-dir /path/to/results
```

Run STAR only on a subject whose active `sphere.reg` files are the native FreeSurfer registrations. The script preserves them as `sphere.reg.backup` before writing STAR registrations.

## Run vertex-wise analysis

```bash
python vertexwise/star_vertexwise_analysis.py \
  --subjects-dir /path/to/freesurfer-subjects \
  --subject SUBJECT_ID \
  --hemi lh \
  --output-dir /path/to/results
```

Use `rh` for a right-operated hemisphere.

## Run validation

```bash
python validation/star_cross_validator.py
```

## Citation

Citation information will be updated after the first Zenodo release of this repository.
