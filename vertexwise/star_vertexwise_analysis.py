#!/usr/bin/env python3
"""Quantify vertex-wise displacement between native and STAR sphere.reg files."""
from __future__ import annotations
import argparse, csv, hashlib, json
from pathlib import Path
from typing import Iterable
import nibabel as nib
import nibabel.freesurfer.io as fsio
import numpy as np

DEFAULT_THRESHOLDS = (0.1, 1.0, 5.0, 10.0, 15.0, 25.0, 40.0, 50.0)

def parse_thresholds(value: str) -> tuple[float, ...]:
    values = tuple(sorted({float(x.strip()) for x in value.split(",") if x.strip()}))
    if not values or any(x < 0 for x in values):
        raise argparse.ArgumentTypeError("Thresholds must be non-negative comma-separated numbers")
    return values

def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def key(prefix: str, threshold: float) -> str:
    return f"{prefix}_gt_{threshold:g}mm".replace(".", "p")

def stats(values: np.ndarray, thresholds: Iterable[float]) -> dict:
    result = {
        "n_vertices": int(values.size),
        "min_displacement_mm": float(np.min(values)),
        "mean_displacement_mm": float(np.mean(values)),
        "median_displacement_mm": float(np.median(values)),
        "p95_displacement_mm": float(np.percentile(values, 95)),
        "max_displacement_mm": float(np.max(values)),
    }
    for threshold in thresholds:
        count = int(np.count_nonzero(values > threshold))
        result[key("vertices", threshold)] = count
        result[key("percent", threshold)] = float(100 * count / values.size)
    return result

def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

def analyze(subject: str, hemi: str, subjects_dir: Path, output_root: Path, thresholds: tuple[float, ...]) -> tuple[dict, list[dict]]:
    subject_dir = subjects_dir / subject
    surf = subject_dir / "surf"
    label = subject_dir / "label"
    native = surf / f"{hemi}.sphere.reg.backup"
    star = surf / f"{hemi}.sphere.reg"
    annot = label / f"{hemi}.aparc.annot"
    for path in (native, star, annot):
        if not path.is_file(): raise FileNotFoundError(path)
    native_coords, _ = fsio.read_geometry(str(native))
    star_coords, _ = fsio.read_geometry(str(star))
    if native_coords.shape != star_coords.shape:
        raise ValueError(f"Coordinate mismatch: {native_coords.shape} vs {star_coords.shape}")
    displacement = np.linalg.norm(native_coords - star_coords, axis=1)
    summary = {"subject": subject, "hemi": hemi, "native_md5": md5(native), "star_md5": md5(star), **stats(displacement, thresholds)}
    labels, _, names = fsio.read_annot(str(annot), orig_ids=False)
    if len(labels) != len(displacement): raise ValueError("Annotation and displacement vertex counts differ")
    regional = []
    for index, raw_name in enumerate(names):
        mask = labels == index
        if np.any(mask):
            name = raw_name.decode() if isinstance(raw_name, bytes) else str(raw_name)
            regional.append({"subject": subject, "hemi": hemi, "region": name, **stats(displacement[mask], thresholds)})
    out = output_root / subject; out.mkdir(parents=True, exist_ok=True)
    stem = f"{subject}_{hemi}_STAR"
    (out / f"{stem}_vertex_displacement_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_csv(out / f"{stem}_regional_vertex_displacement.csv", regional)
    nib.save(nib.MGHImage(displacement.astype(np.float32).reshape((-1, 1, 1)), np.eye(4)), str(out / f"{stem}_vertex_displacement.mgh"))
    (out / f"{stem}_file_provenance.json").write_text(json.dumps({"native": str(native), "star": str(star), "annotation": str(annot)}, indent=2), encoding="utf-8")
    print(f"Subject: {subject}\nHemisphere: {hemi}")
    print(f"Mean displacement: {summary['mean_displacement_mm']:.4f} mm")
    print(f"Median displacement: {summary['median_displacement_mm']:.4f} mm")
    print(f"P95 displacement: {summary['p95_displacement_mm']:.4f} mm")
    print(f"Max displacement: {summary['max_displacement_mm']:.4f} mm")
    return summary, regional

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subjects-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--hemi", choices=("lh", "rh"), required=True)
    parser.add_argument("--thresholds", type=parse_thresholds, default=DEFAULT_THRESHOLDS)
    args = parser.parse_args()
    analyze(args.subject, args.hemi, args.subjects_dir.resolve(), args.output_dir.resolve(), args.thresholds)

if __name__ == "__main__": main()
