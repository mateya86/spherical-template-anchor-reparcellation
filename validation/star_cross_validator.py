"""STAR Cross Validator: native cross-sectional FreeSurfer versus STAR."""

import argparse
import json
import math
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

STATE_FILE = Path("subjects.json")
subjects_data = []
root = inner_frame = canvas = canvas_window = None

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.edgecolor": "#333333", "axes.linewidth": 0.8,
    "axes.grid": True, "grid.color": "#dddddd", "grid.linewidth": 0.6,
    "grid.alpha": 0.6, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.labelsize": 9.5, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
    "legend.fontsize": 8, "legend.frameon": False,
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "savefig.dpi": 300,
})

PANEL_LETTERS = "abcdefghijklmnopqrstuvwxyz"
LOBE_LABELS = ["Frontal", "Parietal", "Temporal", "Occipital"]
LOBE_FULL_NAMES = {
    "Frontal": "Frontal Lobe", "Parietal": "Parietal Lobe",
    "Temporal": "Temporal Lobe", "Occipital": "Occipital Lobe",
}
LOBE_COLORS = {
    "Frontal": "#0072B2", "Parietal": "#CC79A7",
    "Temporal": "#E69F00", "Occipital": "#009E73",
}
BOUNDARY_GYRI = [
    ("Precentral", "precentral", "F|P border"),
    ("Postcentral", "postcentral", "F|P border"),
    ("Precuneus", "precuneus", "P|O border"),
    ("Cuneus", "cuneus", "P|O border"),
    ("Fusiform", "fusiform", "T|O border"),
    ("Lingual", "lingual", "T|O border"),
    ("Sup. Temporal", "superiortemporal", "Temporal"),
    ("Mid. Temporal", "middletemporal", "Temporal"),
]
GYRUS_LABELS = [item[0] for item in BOUNDARY_GYRI]
BORDER_COLORS = {
    "F|P border": "#1565C0", "P|O border": "#E65100",
    "T|O border": "#2E7D32", "Temporal": "#C62828",
}
GRAPH_STYLE = {
    "pre_cross": dict(color="#0072B2", marker="o", markersize=5, linewidth=2,
                      linestyle="solid", label="Pre (native)"),
    "pre_star": dict(color="#E69F00", marker="o", markersize=5, linewidth=2,
                     linestyle="solid", label="Pre (STAR)"),
    "post_cross": dict(color="#0072B2", marker="*", markersize=8, linewidth=2,
                       linestyle="dashed", label="Post (native)"),
    "post_star": dict(color="#E69F00", marker="*", markersize=8, linewidth=2,
                      linestyle="dashed", label="Post (STAR)"),
}
DENOMINATOR_LABEL = "% of brain segmentation volume excluding ventricles"


def _add_panel_label(ax, index):
    ax.text(-0.12, 1.08, f"({PANEL_LETTERS[index % len(PANEL_LETTERS)]})",
            transform=ax.transAxes, fontsize=11, fontweight="bold",
            ha="left", va="bottom", color="#111111")


def load_volume_file(filepath):
    try:
        row = pd.read_csv(filepath, sep=None, engine="python").iloc[0]
        denominator = float(row["BrainSegVolNotVent"])
        if denominator <= 0:
            raise ValueError("BrainSegVolNotVent must be positive")
        if "rh_precentral_volume" in row.index:
            prefix = "rh_"
        elif "lh_precentral_volume" in row.index:
            prefix = "lh_"
        else:
            raise ValueError("Could not detect hemisphere")

        def value(region):
            column = prefix + region + "_volume"
            if column not in row.index:
                raise KeyError(f"Missing required column: {column}")
            return float(row[column])

        regions = {
            "Frontal": ["caudalmiddlefrontal", "lateralorbitofrontal",
                        "medialorbitofrontal", "rostralmiddlefrontal",
                        "superiorfrontal", "parsopercularis", "parsorbitalis",
                        "parstriangularis", "precentral"],
            "Parietal": ["inferiorparietal", "superiorparietal",
                         "supramarginal", "postcentral", "precuneus"],
            "Temporal": ["superiortemporal", "middletemporal",
                         "inferiortemporal", "fusiform", "parahippocampal"],
            "Occipital": ["cuneus", "lateraloccipital", "lingual", "pericalcarine"],
        }
        result = {
            label: sum(value(region) for region in names) / denominator * 100
            for label, names in regions.items()
        }
        for label, column, _ in BOUNDARY_GYRI:
            result[label] = value(column) / denominator * 100
        return result
    except Exception as exc:
        print("=" * 50, f"\nFAILED: {filepath}\n{exc}\n" + "=" * 50)
        return None


def save_subjects():
    data = [{
        "id": row["id"].get(), "pre_cross": row["pre_cross"],
        "pre_star": row["pre_star"], "post_cross": row["post_cross"],
        "post_star": row["post_star"],
    } for row in subjects_data]
    STATE_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
    messagebox.showinfo("Saved", f"Subjects saved to:\n{STATE_FILE}")


def load_subjects():
    if not STATE_FILE.exists():
        return
    try:
        for item in json.loads(STATE_FILE.read_text(encoding="utf-8")):
            add_subject(item.get("id", ""), item.get("pre_cross"),
                        item.get("pre_star"), item.get("post_cross"),
                        item.get("post_star"))
    except Exception as exc:
        messagebox.showwarning("Warning", f"Could not load subjects:\n{exc}")


def add_subject(subject_id="", pre_cross=None, pre_star=None,
                post_cross=None, post_star=None):
    row = {"pre_cross": pre_cross, "pre_star": pre_star,
           "post_cross": post_cross, "post_star": post_star}
    frame = tk.Frame(inner_frame, bg="#f0f0f0", relief="ridge", bd=1)
    frame.pack(anchor="w", pady=3, padx=4, fill="x")
    row["id"] = tk.Entry(frame, width=13, font=("Consolas", 9))
    row["id"].insert(0, subject_id)
    row["id"].pack(side="left", padx=5, pady=4)
    colors = {"Pre native": "#BBDEFB", "Pre STAR": "#FFE0B2",
              "Post native": "#90CAF9", "Post STAR": "#FFCC80"}

    def loader(key, button, label):
        path = filedialog.askopenfilename(title=f"Select {label}")
        if path:
            row[key] = path
            button.config(text=label + " OK", bg="#c8e6c9")

    for key, label in [("pre_cross", "Pre native"), ("pre_star", "Pre STAR"),
                       ("post_cross", "Post native"), ("post_star", "Post STAR")]:
        button = tk.Button(frame, text=f"Load {label}", width=13,
                           bg=colors[label], font=("Consolas", 8))
        button.pack(side="left", padx=2, pady=4)
        button.config(command=lambda k=key, b=button, lab=label: loader(k, b, lab))
        if row[key]:
            button.config(text=label + " OK", bg="#c8e6c9")
    subjects_data.append(row)
    inner_frame.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox("all"))


def _valid_pairs(a, b):
    pairs = [(float(x), float(y)) for x, y in zip(a, b)
             if x is not None and y is not None
             and np.isfinite(float(x)) and np.isfinite(float(y))]
    return np.asarray(pairs, dtype=float)


def compute_delta(star_values, native_values):
    pairs = _valid_pairs(star_values, native_values)
    if len(pairs) == 0:
        return [], None, None
    deltas = pairs[:, 0] - pairs[:, 1]
    sd = np.std(deltas, ddof=1) if len(deltas) > 1 else 0.0
    return deltas.tolist(), float(np.mean(deltas)), float(sd)


def compute_icc_a1(values_a, values_b):
    """Two-way absolute-agreement, single-measure ICC: ICC(A,1)."""
    data = _valid_pairs(values_a, values_b)
    n, k = data.shape if data.ndim == 2 and data.size else (0, 2)
    if n < 2:
        return np.nan, n
    grand = data.mean()
    row_means = data.mean(axis=1)
    column_means = data.mean(axis=0)
    ms_rows = k * np.sum((row_means - grand) ** 2) / (n - 1)
    ms_columns = n * np.sum((column_means - grand) ** 2) / (k - 1)
    residual = data - row_means[:, None] - column_means[None, :] + grand
    ms_error = np.sum(residual ** 2) / ((n - 1) * (k - 1))
    denominator = ms_rows + (k - 1) * ms_error + k * (ms_columns - ms_error) / n
    if np.isclose(denominator, 0):
        return np.nan, n
    return float((ms_rows - ms_error) / denominator), n


def set_dynamic_bias_axis(ax, means, sds):
    """Symmetric bias limits including mean +/- SD with visual padding."""
    extents = [abs(float(mean)) + abs(float(sd)) for mean, sd in zip(means, sds)]
    padded = max(extents, default=0.0) * 1.20
    limit = max(0.05, math.ceil(padded / 0.01) * 0.01)
    if limit > 0.20:
        limit = math.ceil(limit / 0.05) * 0.05
    step = 0.025 if limit <= 0.10 else (0.05 if limit <= 0.20 else 0.10)
    ax.set_ylim(-limit, limit)
    ax.set_yticks(np.arange(-limit, limit + step / 2, step))
    return limit


def collect_data(keys):
    ids = []
    timepoints = ("pre_cross", "pre_star", "post_cross", "post_star")
    store = {tp: {key: [] for key in keys} for tp in timepoints}
    for row in subjects_data:
        ids.append(row["id"].get() or "Patient")
        files = {tp: load_volume_file(row[tp]) if row[tp] else None for tp in timepoints}
        for tp, data in files.items():
            for key in keys:
                store[tp][key].append(data[key] if data else None)
    return ids, store


def save_figure(fig, default_name="figure"):
    path = filedialog.asksaveasfilename(
        title="Save figure", defaultextension=".tif", initialfile=default_name,
        filetypes=[("TIFF image", "*.tif *.tiff"), ("PNG image", "*.png"),
                   ("PDF vector", "*.pdf"), ("All files", "*.*")])
    if path:
        fig.savefig(path, dpi=300, bbox_inches="tight")
        messagebox.showinfo("Saved", f"Figure saved:\n{path}")


def _draw_lines(ax, ids, store, key, timepoints):
    x = np.arange(1, len(ids) + 1)
    for tp in timepoints:
        ax.plot(x, store[tp][key], **GRAPH_STYLE[tp])
    ax.set_xlabel("Patient index")
    ax.set_ylabel(f"Volume\n({DENOMINATOR_LABEL})")
    ax.set_xticks(x)
    ax.set_xticklabels([str(i) for i in x])
    ax.legend(fontsize=7, loc="best")
    ax.tick_params(axis="x", rotation=90 if len(ids) > 12 else 0, labelsize=7.5)
    values = [v for tp in timepoints for v in store[tp][key] if v is not None]
    if values:
        margin = (max(values) - min(values)) * 0.35 or 0.2
        ax.set_ylim(min(values) - margin, max(values) + margin)


def _line_plot(keys, title_prefix, columns):
    ids, store = collect_data(keys)
    rows = (len(keys) + columns - 1) // columns
    configurations = [
        ("Native Pipeline", "Native segmentation only", ["pre_cross", "post_cross"]),
        ("STAR Pipeline", "STAR segmentation only", ["pre_star", "post_star"]),
        ("Native vs. STAR", "Both pipelines overlaid",
         ["pre_cross", "pre_star", "post_cross", "post_star"]),
    ]
    figures = []
    for suffix, subtitle, timepoints in configurations:
        fig, axes = plt.subplots(rows, columns, figsize=(6 * columns, 4.2 * rows),
                                 constrained_layout=True)
        fig.suptitle(f"{title_prefix}: {suffix}\n{subtitle}", fontsize=13, fontweight="bold")
        axes = np.atleast_1d(axes).flatten()
        for index, key in enumerate(keys):
            axes[index].set_title(LOBE_FULL_NAMES.get(key, key))
            _draw_lines(axes[index], ids, store, key, timepoints)
            _add_panel_label(axes[index], index)
        for index in range(len(keys), len(axes)):
            fig.delaxes(axes[index])
        figures.append((fig, suffix))
    plt.show()
    for fig, suffix in figures:
        if messagebox.askyesno("Save Figure", f"Save '{title_prefix} - {suffix}'?"):
            save_figure(fig, title_prefix.replace(" ", "_") + "_" + suffix.replace(" ", "_"))


def _bias_plot(keys, title_prefix, color_map):
    _, store = collect_data(keys)
    pre_means, pre_sds, post_means, post_sds = [], [], [], []
    print("\n" + "=" * 100)
    print(f"BIAS AND ICC - {title_prefix} (Delta = STAR% - native%)")
    print(f"{'Region':<22} {'Pre mean':>10} {'Pre SD':>9} {'Pre ICC':>9} {'n':>4} "
          f"{'Post mean':>11} {'Post SD':>9} {'Post ICC':>10} {'n':>4}")
    print("-" * 100)
    for key in keys:
        _, pre_mean, pre_sd = compute_delta(store["pre_star"][key], store["pre_cross"][key])
        _, post_mean, post_sd = compute_delta(store["post_star"][key], store["post_cross"][key])
        pre_icc, pre_n = compute_icc_a1(store["pre_cross"][key], store["pre_star"][key])
        post_icc, post_n = compute_icc_a1(store["post_cross"][key], store["post_star"][key])
        pre_means.append(pre_mean if pre_mean is not None else 0.0)
        pre_sds.append(pre_sd if pre_sd is not None else 0.0)
        post_means.append(post_mean if post_mean is not None else 0.0)
        post_sds.append(post_sd if post_sd is not None else 0.0)
        fmt = lambda value, signed=False: "n/a" if value is None or not np.isfinite(value) else (f"{value:+.3f}" if signed else f"{value:.3f}")
        print(f"{key:<22} {fmt(pre_mean, True):>10} {fmt(pre_sd):>9} {fmt(pre_icc):>9} {pre_n:>4} "
              f"{fmt(post_mean, True):>11} {fmt(post_sd):>9} {fmt(post_icc):>10} {post_n:>4}")
    print("=" * 100)

    x = np.arange(len(keys))
    width = 0.28
    colors = [color_map[key] for key in keys]
    fig, ax = plt.subplots(figsize=(max(11, len(keys) * 1.5), 6), constrained_layout=True)
    for index, (mean, sd, color) in enumerate(zip(pre_means, pre_sds, colors)):
        ax.bar(index - width / 2, mean, width, color=color, alpha=.9, yerr=sd,
               capsize=4, error_kw={"elinewidth": 1.5, "ecolor": "black"})
    for index, (mean, sd, color) in enumerate(zip(post_means, post_sds, colors)):
        bars = ax.bar(index + width / 2, mean, width, color=color, alpha=.9,
                      hatch="ooo", yerr=sd, capsize=4,
                      error_kw={"elinewidth": 1.5, "ecolor": "black"})
        for bar in bars:
            bar.set_edgecolor("black")
            bar.set_linewidth(0)
    ax.axhline(0, color="black", linewidth=1.2, linestyle="--", alpha=.6)
    axis_limit = set_dynamic_bias_axis(
        ax,
        pre_means + post_means,
        pre_sds + post_sds,
    )

    # Keep preoperative and postoperative mean +/- SD labels in separate lanes.
    # Labels are placed beyond each error-bar endpoint and shifted left/right.
    vertical_gap = axis_limit * 0.045
    lane_gap = axis_limit * 0.085
    for index, (pre_mean, pre_sd, post_mean, post_sd) in enumerate(
        zip(pre_means, pre_sds, post_means, post_sds)
    ):
        label_specs = [
            (index - width / 2, pre_mean, pre_sd, -7, 0, "right"),
            (index + width / 2, post_mean, post_sd, 7, 1, "left"),
        ]
        for xpos, mean, sd, x_offset, lane, horizontal_alignment in label_specs:
            sign = 1 if mean >= 0 else -1
            error_endpoint = mean + sign * abs(sd)
            label_y = error_endpoint + sign * (vertical_gap + lane * lane_gap)
            ax.annotate(
                f"{mean:+.3f} +/- {sd:.3f}",
                xy=(xpos, label_y),
                xytext=(x_offset, 0),
                textcoords="offset points",
                ha=horizontal_alignment,
                va="bottom" if sign > 0 else "top",
                fontsize=6.3,
                clip_on=False,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.75, "pad": 0.3},
            )
    handles = [Patch(facecolor=color_map[key], label=LOBE_FULL_NAMES.get(key, key)) for key in keys]
    handles += [Patch(facecolor="grey", label="Pre-operative"),
                Patch(facecolor="grey", hatch="ooo", edgecolor="black", label="Post-operative")]
    ax.legend(handles=handles, fontsize=8, loc="upper right", ncol=2)
    ax.set_xticks(x)
    ax.set_xticklabels([LOBE_FULL_NAMES.get(key, key) for key in keys], rotation=30, ha="right")
    ax.set_ylabel(f"Regional volume bias (STAR - native)\n({DENOMINATOR_LABEL})")
    ax.set_title(f"Pipeline Bias in Regional Volume Estimation - {title_prefix}")
    _add_panel_label(ax, 0)
    plt.show()
    if messagebox.askyesno("Save Figure", f"Save bias figure '{title_prefix}'?"):
        save_figure(fig, "Bias_" + title_prefix.replace(" ", "_"))


def _long_delta_concordance(keys, title_prefix, color_map):
    ids, store = collect_data(keys)
    native = {key: [] for key in keys}
    star = {key: [] for key in keys}
    bias = {key: [] for key in keys}
    valid_ids = []
    for index, patient_id in enumerate(ids):
        if any(store[tp][key][index] is None for tp in
               ("pre_cross", "pre_star", "post_cross", "post_star") for key in keys):
            continue
        valid_ids.append(patient_id)
        for key in keys:
            native_delta = store["post_cross"][key][index] - store["pre_cross"][key][index]
            star_delta = store["post_star"][key][index] - store["pre_star"][key][index]
            native[key].append(native_delta)
            star[key].append(star_delta)
            bias[key].append(star_delta - native_delta)
    if not valid_ids:
        messagebox.showwarning("No data", "Select all four files for at least one patient.")
        return

    print("\n" + "=" * 90)
    print(f"LONGITUDINAL CONCORDANCE AND ICC - {title_prefix}")
    print(f"{'Region':<22} {'Mean native':>12} {'Mean STAR':>11} {'Bias':>10} {'SD':>9} {'ICC(A,1)':>10} {'n':>4}")
    for key in keys:
        icc, n = compute_icc_a1(native[key], star[key])
        sd = np.std(bias[key], ddof=1) if n > 1 else 0.0
        print(f"{key:<22} {np.mean(native[key]):>+12.3f} {np.mean(star[key]):>+11.3f} "
              f"{np.mean(bias[key]):>+10.3f} {sd:>9.3f} {icc:>10.3f} {n:>4}")
    print("=" * 90)

    columns = min(4, len(keys))
    rows = (len(keys) + columns - 1) // columns
    fig1, axes = plt.subplots(rows, columns, figsize=(5 * columns, 4.9 * rows),
                              constrained_layout=True)
    fig1.suptitle(f"Concordance of Longitudinal Volume Change - {title_prefix}\n"
                  "Dashed line = perfect agreement", fontweight="bold")
    axes = np.atleast_1d(axes).flatten()
    for index, key in enumerate(keys):
        ax = axes[index]
        xvalues, yvalues = np.asarray(native[key]), np.asarray(star[key])
        lower = min(xvalues.min(), yvalues.min()) - .05
        upper = max(xvalues.max(), yvalues.max()) + .05
        ax.plot([lower, upper], [lower, upper], "k--", alpha=.5)
        ax.scatter(xvalues, yvalues, color=color_map[key], s=55,
                   edgecolor="white", linewidth=.5)
        icc, _ = compute_icc_a1(xvalues, yvalues)
        ax.text(.05, .92, f"ICC(A,1) = {icc:.2f}", transform=ax.transAxes,
                fontsize=8, color=color_map[key])
        ax.set_title(LOBE_FULL_NAMES.get(key, key))
        ax.set_xlabel(f"Longitudinal change, native\n({DENOMINATOR_LABEL})", fontsize=7.5)
        ax.set_ylabel(f"Longitudinal change, STAR\n({DENOMINATOR_LABEL})", fontsize=7.5)
        ax.set_xlim(lower, upper)
        ax.set_ylim(lower, upper)
        ax.set_aspect("equal", adjustable="box")
        _add_panel_label(ax, index)
    for index in range(len(keys), len(axes)):
        fig1.delaxes(axes[index])

    means = [np.mean(bias[key]) for key in keys]
    sds = [np.std(bias[key], ddof=1) if len(bias[key]) > 1 else 0 for key in keys]
    fig2, ax2 = plt.subplots(figsize=(max(10, len(keys) * 1.5), 5.5), constrained_layout=True)
    x = np.arange(len(keys))
    ax2.bar(x, means, .38, color=[color_map[key] for key in keys], alpha=.88,
            yerr=sds, capsize=5, error_kw={"elinewidth": 1.5, "ecolor": "black"})
    ax2.axhline(0, color="black", linestyle="--", alpha=.6)
    longitudinal_axis_limit = set_dynamic_bias_axis(ax2, means, sds)
    for index, (mean, sd) in enumerate(zip(means, sds)):
        sign = 1 if mean >= 0 else -1
        ax2.annotate(
            f"{mean:+.3f} +/- {sd:.3f}",
            (index, mean + sign * (abs(sd) + longitudinal_axis_limit * 0.05)),
            ha="center",
            va="bottom" if sign > 0 else "top",
            fontsize=7,
            clip_on=False,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.75, "pad": 0.3},
        )
    ax2.set_xticks(x)
    ax2.set_xticklabels([LOBE_FULL_NAMES.get(key, key) for key in keys], rotation=30, ha="right")
    ax2.set_ylabel(f"Longitudinal-change bias (STAR - native)\n({DENOMINATOR_LABEL})")
    ax2.set_title(f"Bias in Longitudinal Volume Change - {title_prefix}")
    _add_panel_label(ax2, 0)
    plt.show()
    for figure, name in [(fig1, "LongConc_Scatter_" + title_prefix.replace(" ", "_")),
                         (fig2, "LongConc_Bias_" + title_prefix.replace(" ", "_"))]:
        if messagebox.askyesno("Save Figure", f"Save '{name}'?"):
            save_figure(figure, name)


def gyrus_colors():
    return {item[0]: BORDER_COLORS[item[2]] for item in BOUNDARY_GYRI}


def build_app():
    global root, inner_frame, canvas, canvas_window
    root = tk.Tk()
    root.title("STAR Cross Validator - ICC(A,1)")
    root.geometry("1350x780")
    top = tk.Frame(root, bg="#e8eaf6", pady=6)
    top.pack(fill="x")
    actions = [
        ("Add Subject", add_subject),
        ("Lobe Graph", lambda: _line_plot(LOBE_LABELS, "Lobe Volumes", 3)),
        ("Lobe Bias + ICC", lambda: _bias_plot(LOBE_LABELS, "Lobes", LOBE_COLORS)),
        ("Lobe Long. ICC", lambda: _long_delta_concordance(LOBE_LABELS, "Lobes", LOBE_COLORS)),
        ("Boundary Gyri Graph", lambda: _line_plot(GYRUS_LABELS, "Boundary Gyri Volumes", 4)),
        ("Gyri Bias + ICC", lambda: _bias_plot(GYRUS_LABELS, "Boundary Gyri", gyrus_colors())),
        ("Gyri Long. ICC", lambda: _long_delta_concordance(GYRUS_LABELS, "Boundary Gyri", gyrus_colors())),
        ("Save Subjects", save_subjects),
    ]
    for label, command in actions:
        tk.Button(top, text=label, command=command, width=17, height=2,
                  bg="#3F51B5", fg="white", font=("Consolas", 9, "bold"),
                  relief="flat").pack(side="left", padx=5, pady=4)
    scroll_frame = tk.Frame(root)
    scroll_frame.pack(fill="both", expand=True, padx=4, pady=4)
    canvas = tk.Canvas(scroll_frame, bg="#f0f0f0", highlightthickness=0)
    scrollbar = tk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner_frame = tk.Frame(canvas, bg="#f0f0f0")
    canvas_window = canvas.create_window((0, 0), window=inner_frame, anchor="nw")
    canvas.bind("<Configure>", lambda event: canvas.itemconfig(canvas_window, width=event.width))
    canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-event.delta / 120), "units"))
    canvas.bind_all("<Button-4>", lambda event: canvas.yview_scroll(-1, "units"))
    canvas.bind_all("<Button-5>", lambda event: canvas.yview_scroll(1, "units"))
    load_subjects()
    return root


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-file", type=Path, default=Path("subjects.json"),
                        help="Local JSON state file (default: subjects.json)")
    return parser.parse_args()


def main():
    global STATE_FILE
    args = parse_args()
    STATE_FILE = args.state_file.expanduser()
    build_app().mainloop()


if __name__ == "__main__":
    main()
