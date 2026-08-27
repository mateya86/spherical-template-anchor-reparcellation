#!/usr/bin/env python3
"""Create a binned FreeSurfer annotation from a STAR displacement MGH file."""
import argparse, csv
from pathlib import Path
import nibabel as nib
import nibabel.freesurfer.io as fsio
import numpy as np
EDGES=(0.,5.,15.,25.,40.,50.,float("inf"))
NAMES=("lt5mm_neutral","5-15mm_lightyellow","15-25mm_yellow","25-40mm_orange","40-50mm_red","gt50mm_darkred")
RGB=np.array([[225,225,225],[255,255,170],[255,255,0],[255,140,0],[255,0,0],[130,0,0]],dtype=np.int32)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--displacement-mgh",type=Path,required=True);p.add_argument("--output-annot",type=Path,required=True);p.add_argument("--legend-csv",type=Path,required=True)
    a=p.parse_args(); values=np.squeeze(nib.load(str(a.displacement_mgh)).get_fdata())
    if values.ndim!=1: raise ValueError(f"Expected 1D displacement data, got {values.shape}")
    labels=np.zeros(values.size,dtype=np.int32)
    for i,(lo,hi) in enumerate(zip(EDGES[:-1],EDGES[1:])): labels[(values>=lo)&(values<hi)]=i
    ctab=np.zeros((6,5),dtype=np.int32);ctab[:,:3]=RGB;ctab[:,4]=RGB[:,0]+(RGB[:,1]<<8)+(RGB[:,2]<<16)
    a.output_annot.parent.mkdir(parents=True,exist_ok=True)
    fsio.write_annot(str(a.output_annot),labels,ctab,[x.encode() for x in NAMES],fill_ctab=False)
    with a.legend_csv.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(["bin","range_mm","color"]);w.writerows(enumerate(["<5","5-15","15-25","25-40","40-50",">50"]))
    print(f"Created: {a.output_annot}\nLegend: {a.legend_csv}")
if __name__=="__main__": main()
