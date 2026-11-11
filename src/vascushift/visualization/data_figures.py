"""; Figures of the real-data pipeline (rPPG baseline on UBFC, physiology vs gravity vector).; ; Static PNGs for the poster/report; the interactive versions live in the dashboard (demo/).; Style follows one fixed token set (light surface): categorical slots in a fixed order, hairline; recessive grid, text in ink tokens (never in series colour), thin marks, a legend whenever >= 2; series. Method -> colour is fixed (never depends on rank or on which methods are plotted).; """

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

TOKENS = {
    "surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
    "grid": "#e1e0d9", "axis": "#c3c2b7",
}
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
METHOD_COLOR = {"pos": SERIES[0], "chrom": SERIES[1], "green": SERIES[2]}
METHOD_LABEL = {"pos": "POS", "chrom": "CHROM", "green": "Green"}
PROTOCOL_LABEL = {"whole": "Whole recording", "w30s15": "30 s windows", "w10s2": "10 s windows"}


def _style():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.facecolor": TOKENS["surface"], "axes.facecolor": TOKENS["surface"],
        "savefig.facecolor": TOKENS["surface"], "axes.edgecolor": TOKENS["axis"], "axes.linewidth": 0.8,
        "axes.labelcolor": TOKENS["ink2"], "xtick.color": TOKENS["muted"], "ytick.color": TOKENS["muted"],
        "xtick.labelcolor": TOKENS["ink2"], "ytick.labelcolor": TOKENS["ink2"],
        "axes.grid": True, "grid.color": TOKENS["grid"], "grid.linewidth": 0.8, "grid.linestyle": "-",
        "axes.spines.top": False, "axes.spines.right": False, "axes.titlecolor": TOKENS["ink"],
        "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "font.size": 9.5, "legend.frameon": False, "legend.labelcolor": TOKENS["ink2"],
        "lines.linewidth": 2.0, "lines.solid_capstyle": "round", "text.color": TOKENS["ink"],
    })
    return plt


def _caption(fig, text: str):
    fig.text(0.01, 0.005, text, color=TOKENS["muted"], fontsize=7.5, ha="left", va="bottom")


# --------------------------------------------------------------------------------------------- rPPG
def fig_rppg_mae_by_protocol(summary: pd.DataFrame, out: Path) -> Path:
    """Dot + 95 % CI whisker: MAE per method x protocol, one panel per UBFC subset."""
    plt = _style()
    subsets = [s for s in ("DATASET_2", "DATASET_1") if s in set(summary["subset"])]
    fig, axes = plt.subplots(1, len(subsets), figsize=(4.2 * len(subsets), 3.6), sharey=True, squeeze=False)
    protos = [p for p in PROTOCOL_LABEL if p in set(summary["protocol"])]
    methods = [m for m in METHOD_COLOR if m in set(summary["method"])]
    off = np.linspace(-0.22, 0.22, len(methods))
    for ax, sub in zip(axes[0], subsets):
        d = summary[summary.subset == sub]
        for j, m in enumerate(methods):
            r = d[d.method == m].set_index("protocol").reindex(protos)
            x = np.arange(len(protos)) + off[j]
            ax.vlines(x, r.mae_ci_low, r.mae_ci_high, color=METHOD_COLOR[m], lw=2)
            ax.scatter(x, r.mae_bpm, s=46, color=METHOD_COLOR[m], edgecolor=TOKENS["surface"], linewidth=2,
                       zorder=3, label=METHOD_LABEL[m])
        n = int(d["n_sessions"].max())
        ax.set_title(f"UBFC-rPPG {sub.replace('DATASET_', 'DATASET ')} · {n} sessions")
        ax.set_xticks(range(len(protos)), [PROTOCOL_LABEL[p] for p in protos])
        ax.grid(axis="x", visible=False)
        ax.set_ylim(bottom=0)
    axes[0][0].set_ylabel("Heart-rate MAE [bpm]  (dot = MAE, line = 95 % CI)")
    axes[0][-1].legend(loc="upper right", ncols=1)
    _caption(fig, "Real data. Reference: contact finger PPG, same filter and HR estimator. "
                  "CI: bootstrap over sessions. Windows with <90 % measured samples excluded.")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def fig_rppg_scatter(windows: pd.DataFrame, out: Path, subset: str = "DATASET_2", protocol: str = "w10s2") -> Path:
    """Small multiples: estimated vs reference HR per method, with identity and ±5 bpm band."""
    plt = _style()
    d = windows[(windows.subset == subset) & (windows.protocol == protocol) & windows.included]
    methods = [m for m in ("green", "chrom", "pos") if m in set(d.method)]
    lo, hi = 40, 150
    fig, axes = plt.subplots(1, len(methods), figsize=(3.3 * len(methods), 3.8), sharey=True)
    for ax, m in zip(np.atleast_1d(axes), methods):
        r = d[d.method == m]
        ax.fill_between([lo, hi], [lo - 5, hi - 5], [lo + 5, hi + 5], color=TOKENS["grid"], alpha=0.6, lw=0)
        ax.plot([lo, hi], [lo, hi], color=TOKENS["axis"], lw=1)
        ax.scatter(r.hr_ref_bpm, r.hr_est_bpm.clip(lo, hi), s=9, color=METHOD_COLOR[m], alpha=0.45, lw=0)
        within = (r.error_bpm.abs() <= 5).mean() * 100
        ax.set_title(f"{METHOD_LABEL[m]}  ·  {within:.0f} % within ±5 bpm")
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_aspect("equal")
        ax.set_xlabel("Reference HR, finger PPG [bpm]")
    np.atleast_1d(axes)[0].set_ylabel("rPPG HR [bpm] (clipped to 40–150)")
    n_s, n_w = d.session_id.nunique(), len(d) // max(1, len(methods))
    _caption(fig, f"UBFC-rPPG {subset}, {PROTOCOL_LABEL[protocol].lower()} (stride 2 s): {n_w} windows from {n_s} "
                  "sessions. Grey band: ±5 bpm.")
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def fig_rppg_bland_altman(windows: pd.DataFrame, out: Path, method: str = "pos", subset: str = "DATASET_2",
                          protocol: str = "w10s2") -> Path:
    plt = _style()
    d = windows[(windows.subset == subset) & (windows.protocol == protocol) & (windows.method == method) & windows.included]
    mean = (d.hr_ref_bpm + d.hr_est_bpm) / 2
    diff = d.error_bpm
    bias, sd = diff.mean(), diff.std(ddof=1)
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    ax.scatter(mean, diff.clip(-40, 40), s=10, color=METHOD_COLOR[method], alpha=0.45, lw=0)
    for y, lab in ((bias, f"bias {bias:+.2f}"), (bias + 1.96 * sd, f"+1.96 SD {bias + 1.96 * sd:+.1f}"),
                   (bias - 1.96 * sd, f"−1.96 SD {bias - 1.96 * sd:+.1f}")):
        ax.axhline(y, color=TOKENS["ink2"] if lab.startswith("bias") else TOKENS["muted"], lw=1)
        ax.text(ax.get_xlim()[1], y, f" {lab} bpm", va="center", ha="left", color=TOKENS["ink2"], fontsize=8)
    ax.set_xlabel("Mean of rPPG and reference HR [bpm]")
    ax.set_ylabel("rPPG − reference [bpm] (clipped ±40)")
    ax.set_title(f"Bland–Altman · {METHOD_LABEL[method]} · UBFC {subset.replace('DATASET_', 'D')} · "
                 f"{PROTOCOL_LABEL[protocol].lower()}")
    inner = (diff.abs() <= 1.96 * sd).mean() * 100
    _caption(fig, f"{len(d)} windows, {d.session_id.nunique()} sessions; {inner:.0f} % inside the limits of agreement. "
                  "Real data.")
    fig.tight_layout(rect=(0, 0.04, 0.86, 1))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def fig_rppg_session_errors(windows: pd.DataFrame, out: Path) -> Path:
    """Whole-recording signed error per session (sorted by POS), all methods, on a symlog axis (linear in ±5)."""
    plt = _style()
    w = windows[(windows.protocol == "whole")].pivot_table(index=["session_id", "subset"], columns="method",
                                                             values="error_bpm").reset_index()
    w = w.sort_values(["subset", "pos"], ascending=[False, True]).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(9.5, 4.0))
    x = np.arange(len(w))
    for m in ("green", "chrom", "pos"):
        if m in w:
            ax.scatter(x, w[m], s=30, color=METHOD_COLOR[m], edgecolor=TOKENS["surface"], lw=1.5, zorder=3,
                       label=METHOD_LABEL[m])
    ax.set_yscale("symlog", linthresh=5, linscale=1.5)
    ax.set_yticks([-80, -40, -20, -10, -5, 0, 5, 10, 20])
    ax.set_yticklabels(["−80", "−40", "−20", "−10", "−5", "0", "5", "10", "20"])
    ax.axhspan(-5, 5, color=TOKENS["grid"], alpha=0.6, lw=0)
    ax.axhline(0, color=TOKENS["axis"], lw=1)
    nd2 = int((w.subset == "DATASET_2").sum())
    if 0 < nd2 < len(w):
        ax.axvline(nd2 - 0.5, color=TOKENS["axis"], lw=1)
        ax.text(nd2 / 2, 25, f"DATASET 2 ({nd2})", ha="center", color=TOKENS["ink2"], fontsize=8)
        ax.text(nd2 + (len(w) - nd2) / 2, 25, f"DATASET 1 ({len(w) - nd2})", ha="center", color=TOKENS["ink2"], fontsize=8)
    ax.set_ylim(-100, 40)
    ax.set_xticks([])
    ax.grid(axis="x", visible=False)
    ax.set_xlabel("Sessions, sorted by POS error within each subset")
    ax.set_ylabel("Whole-recording HR error [bpm] (symlog)")
    ax.set_title("Per-session HR error of each method")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.06), ncols=3, borderaxespad=0)
    _caption(fig, "Grey band: ±5 bpm (axis linear inside it, logarithmic outside). Real UBFC-rPPG data; "
                  "one HR estimate per recording.")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def make_rppg_figures(baseline_dir: Path = Path("reports/rppg_baseline"),
                      fig_dir: Optional[Path] = None) -> Dict[str, Path]:
    baseline_dir = Path(baseline_dir)
    fig_dir = Path(fig_dir) if fig_dir else baseline_dir / "figures"
    summary = pd.read_csv(baseline_dir / "summary.csv")
    windows = pd.read_csv(baseline_dir / "windows.csv")
    extra = {}
    imp = baseline_dir.parent / "rppg_improved" / "windows.csv"
    if imp.exists():
        extra["improvement"] = fig_rppg_improvement(windows, pd.read_csv(imp),
                                                    baseline_dir.parent / "rppg_improved" / "figures" / "rppg_improvement_holdout.png")
    return {**extra,
        "mae_by_protocol": fig_rppg_mae_by_protocol(summary, fig_dir / "rppg_mae_by_protocol.png"),
        "scatter_w10s2": fig_rppg_scatter(windows, fig_dir / "rppg_scatter_d2_w10s2.png"),
        "bland_altman_pos": fig_rppg_bland_altman(windows, fig_dir / "rppg_bland_altman_pos_d2_w10s2.png"),
        "session_errors": fig_rppg_session_errors(windows, fig_dir / "rppg_session_errors_whole.png"),
    }


# --------------------------------------------------------------------------------------- physiology
ENV_STYLE = {  # colour = environment (neutral ink for the 1 G ground reference), marker = study
    "ground": {"color": TOKENS["ink2"], "label": "Ground, 1 G"},
    "parabolic_flight": {"color": SERIES[1], "label": "Parabolic flight (0–0.75 G)"},
    "iss": {"color": SERIES[2], "label": "ISS, 0 G (free-floating)"},
}
STUDY_MARKER = {"lee2020_partial_gravity": ("o", "Lee 2020"), "marshall_goebel2019_iss_ijv": ("s", "Marshall-Goebel 2019"),
                "martin2016_parabolic_ijvp": ("D", "Martin 2016")}


def _env_group(env: str, gz_platform: float) -> str:
    if str(env).startswith("iss"):
        return "iss"
    if str(env) == "parabolic_flight" and gz_platform < 1:
        return "parabolic_flight"
    return "ground"


def fig_variable_vs_gz(cond_stats: pd.DataFrame, anchors: pd.DataFrame, base_var: str, ylabel: str, out: Path,
                       log: bool = False, raw_dataset: str = "bhp_carotid_jugular", title: str = "") -> Path:
    """Two panels on one y-axis: (A) individual ground-tilt data, median + IQR per gz_body; (B) published means."""
    plt = _style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.1), sharey=True, gridspec_kw={"width_ratios": [1.15, 1]})
    cs = cond_stats[(cond_stats.dataset == raw_dataset) & (cond_stats.variable == base_var)]
    blue = SERIES[0]
    n_max = 0
    for fam, ls in (("supine", "-"), ("prone", "--")):
        d = cs[(cs.family == fam) & (cs.lbnp_mmHg.fillna(0) == 0)].sort_values("gz_body")
        if d.empty:
            continue
        n_max = max(n_max, int(d.n_subjects.max()))
        ax1.fill_between(d.gz_body, d.q1, d.q3, color=blue, alpha=0.10 if fam == "supine" else 0.06, lw=0)
        ax1.plot(d.gz_body, d["median"], color=blue, ls=ls, lw=2, label=f"{fam.capitalize()} tilt, median (IQR band)")
        ax1.scatter(d.gz_body, d["median"], s=30, color=blue, edgecolor=TOKENS["surface"], lw=1.5, zorder=3)
    seated = cs[cs.family == "seated"]
    if len(seated):
        r = seated.iloc[0]
        ax1.errorbar([r.gz_body], [r["median"]], yerr=[[r["median"] - r.q1], [r.q3 - r["median"]]], fmt="o",
                     ms=7, mfc=TOKENS["surface"], mec=blue, mew=2, ecolor=blue, elinewidth=2, capsize=0,
                     label=f"Seated, median (IQR), n = {int(r.n_subjects)}", zorder=3)
    ax1.set_title(f"A · Ground tilt, individual data (n ≤ {n_max})")
    ax1.set_xlabel("gz_body = sin(tilt) [g]   (−: head-down, +: head-up)")
    ax1.set_ylabel(ylabel)
    ax1.legend(loc="upper right" if not log else "lower left")

    a = anchors[(anchors.base == base_var) & (anchors.lbnp_mmHg.fillna(0) == 0)].copy()
    a["env"] = [_env_group(e, g) for e, g in zip(a.environment, a.gz_platform.fillna(1))]
    jitter = {"lee2020_partial_gravity": -0.02, "marshall_goebel2019_iss_ijv": 0.02, "martin2016_parabolic_ijvp": 0.0}
    seen_env, seen_study = set(), set()
    for _, r in a.dropna(subset=["value", "gz_body"]).iterrows():
        x = r.gz_body + jitter.get(r.dataset, 0) + (0.035 if r.condition == "iss_fd150" else 0)
        if r.stat == "mean_sd":
            lo, hi = r.value - r.sd, r.value + r.sd
        else:
            lo, hi = r.ci_low, r.ci_high
        if log:
            lo = max(lo, 1.0) if pd.notna(lo) else lo
        col = ENV_STYLE[r.env]["color"]
        mk = STUDY_MARKER.get(r.dataset, ("o", r.dataset))[0]
        if pd.notna(lo) and pd.notna(hi):
            ax2.vlines(x, lo, hi, color=col, lw=2)
        ax2.scatter([x], [r.value], marker=mk, s=44, color=col, edgecolor=TOKENS["surface"], lw=1.5, zorder=3)
        seen_env.add(r.env)
        seen_study.add(r.dataset)
    from matplotlib.lines import Line2D

    handles = [Line2D([], [], color=ENV_STYLE[e]["color"], lw=2, label=ENV_STYLE[e]["label"]) for e in ENV_STYLE if e in seen_env]
    handles += [Line2D([], [], ls="", marker=STUDY_MARKER[s][0], color=TOKENS["ink2"], mfc="none", label=STUDY_MARKER[s][1])
                for s in STUDY_MARKER if s in seen_study]
    ax2.legend(handles=handles, loc="upper right" if not log else "lower left", fontsize=8)
    ax2.set_title("B · Published group means (95 % CI or ±SD)")
    ax2.set_xlabel("gz_body [g]  (ISS and supine: 0)")
    for ax in (ax1, ax2):
        ax.axvline(0, color=TOKENS["axis"], lw=1, zorder=0)
        ax.set_xlim(-0.8, 1.1)
        if log:
            ax.set_yscale("log")
            from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

            ax.yaxis.set_major_locator(FixedLocator([2, 5, 10, 20, 50, 100, 200, 400]))
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
            ax.yaxis.set_minor_locator(NullLocator())
    if title:
        fig.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold", color=TOKENS["ink"])
    _caption(fig, "Real data only. A: Whittle & Diaz-Artiles 2023 (BHP-Lab, MIT licence), left/right averaged. "
                  "B: transcribed from the papers' tables. No synthetic values.")
    fig.tight_layout(rect=(0, 0.04, 1, 0.95 if title else 1))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def fig_prcp_hr(subject_level: pd.DataFrame, out: Path) -> Path:
    """PhysioNet PRCP: HR per subject across supine -> 75 deg head-up tilt -> standing."""
    plt = _style()
    d = subject_level[(subject_level.dataset == "physionet_prcp") & (subject_level.variable == "heart_rate")]
    order = ["supine", "hut75", "standing"]
    piv = d.pivot_table(index="subject_id", columns="condition", values="value").reindex(columns=order)
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    x = np.arange(len(order))
    for _, row in piv.iterrows():
        ax.plot(x, row.values, color=TOKENS["grid"], lw=1.2, zorder=1)
    med = piv.median()
    ax.plot(x, med.values, color=SERIES[0], lw=2, zorder=2)
    ax.scatter(x, med.values, s=40, color=SERIES[0], edgecolor=TOKENS["surface"], lw=1.5, zorder=3)
    for xi, v in zip(x, med.values):
        ax.text(xi + 0.06, v, f"{v:.0f}", color=TOKENS["ink2"], fontsize=8.5, va="center")
    ax.set_xticks(x, ["Supine\n(gz_body ≈ 0)", "75° head-up tilt\n(≈ 0.96)", "Standing\n(1.0)"])
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Heart rate [bpm], median of beats")
    ax.set_title(f"HR rises with head-to-foot gravity · n = {len(piv)}")
    _caption(fig, "PhysioNet PRCP (ODC-By). Grey: individuals; blue: median. Steady 60 s plateaus.")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def fig_lbnp(cond_stats: pd.DataFrame, out: Path, base_var: str = "ijv_area") -> Path:
    """INTERNAL (unlicensed data): IJV area vs LBNP level, supine and 15 deg head-down."""
    plt = _style()
    cs = cond_stats[(cond_stats.dataset == "bhp_lbnp_dose_response") & (cond_stats.variable == base_var)].copy()
    cs["series"] = cs.condition.str.split("_lbnp").str[0]
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    for ser, ls, lab in (("supine", "-", "Supine"), ("hdt15", "--", "15° head-down")):
        d = cs[cs.series == ser].sort_values("lbnp_mmHg", ascending=False)
        if d.empty:
            continue
        ax.fill_between(-d.lbnp_mmHg, d.q1, d.q3, color=SERIES[0], alpha=0.08, lw=0)
        ax.plot(-d.lbnp_mmHg, d["median"], color=SERIES[0], ls=ls, lw=2, label=f"{lab}, median (IQR)")
        ax.scatter(-d.lbnp_mmHg, d["median"], s=30, color=SERIES[0], edgecolor=TOKENS["surface"], lw=1.5, zorder=3)
    ax.set_xlabel("Lower-body negative pressure [−mmHg]")
    ax.set_ylabel("IJV cross-sectional area [mm²]")
    ax.set_title("IJV area under LBNP · INTERNAL, do not publish")
    ax.legend(loc="upper right")
    _caption(fig, "BHP-Lab LBNP-Dose-Response (no licence: team use only, do not publish). n = 24.")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def make_physiology_figures(analysis_dir: Path = Path("reports/physiology_real")) -> Dict[str, Path]:
    analysis_dir = Path(analysis_dir)
    figs = analysis_dir / "figures"
    cs = pd.read_csv(analysis_dir / "condition_stats.csv")
    an = pd.read_csv(analysis_dir / "literature_anchors.csv")
    sl = pd.read_csv(analysis_dir / "subject_level.csv")
    out = {
        "ijv_area_vs_gz": fig_variable_vs_gz(cs, an, "ijv_area", "IJV cross-sectional area [mm²] (log)",
                                             figs / "ijv_area_vs_gz_body.png", log=True),
        "ijv_pressure_vs_gz": fig_variable_vs_gz(cs, an, "ijv_pressure", "IJV pressure [mmHg]",
                                                 figs / "ijv_pressure_vs_gz_body.png", log=False),
        "prcp_hr": fig_prcp_hr(sl, figs / "prcp_hr_by_posture.png"),
    }
    rb = analysis_dir.parent / "rppg_baseline" / "windows.csv"
    if rb.exists():
        out["poster_two_layers"] = fig_poster_two_layers(pd.read_csv(rb), cs, an,
                                                         analysis_dir.parent / "figures" / "data" / "poster_two_layers.png")
    internal = analysis_dir / "internal"
    if (internal / "condition_stats.csv").exists():
        csi = pd.read_csv(internal / "condition_stats.csv")
        if (csi.dataset == "bhp_lbnp_dose_response").any():
            out["lbnp_internal"] = fig_lbnp(csi, internal / "figures" / "ijv_area_vs_lbnp_INTERNAL.png")
    return out


def fig_poster_two_layers(windows: pd.DataFrame, cond_stats: pd.DataFrame, anchors: pd.DataFrame, out: Path) -> Path:
    """Poster panel: the two layers validated separately on real data (optical | physiology)."""
    plt = _style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={"width_ratios": [1, 1.25]})
    d = windows[(windows.subset == "DATASET_2") & (windows.protocol == "w10s2") & (windows.method == "pos") & windows.included]
    lo, hi = 45, 140
    ax1.fill_between([lo, hi], [lo - 5, hi - 5], [lo + 5, hi + 5], color=TOKENS["grid"], alpha=0.7, lw=0)
    ax1.plot([lo, hi], [lo, hi], color=TOKENS["axis"], lw=1)
    ax1.scatter(d.hr_ref_bpm, d.hr_est_bpm.clip(lo, hi), s=8, color=SERIES[0], alpha=0.4, lw=0)
    e = d.error_bpm
    ax1.set_xlim(lo, hi)
    ax1.set_ylim(lo, hi)
    ax1.set_aspect("equal")
    ax1.set_xlabel("Finger pulse oximeter HR [bpm]")
    ax1.set_ylabel("Face-video HR, POS [bpm]")
    ax1.set_title("A · Optical layer: heart rate from a face camera")
    ax1.text(lo + 3, hi - 4, f"MAE {e.abs().mean():.1f} bpm · {(e.abs() <= 5).mean() * 100:.0f} % within ±5 bpm\n"
             f"{d.session_id.nunique()} people · {len(d)} ten-second windows", va="top", fontsize=8.5, color=TOKENS["ink2"])

    cs = cond_stats[(cond_stats.dataset == "bhp_carotid_jugular") & (cond_stats.variable == "ijv_area") &
                    (cond_stats.family == "supine")].sort_values("gz_body")
    ax2.fill_between(cs.gz_body, cs.q1, cs.q3, color=SERIES[0], alpha=0.10, lw=0)
    ax2.plot(cs.gz_body, cs["median"], color=SERIES[0], lw=2, label=f"Ground tilt, median (IQR), n = {int(cs.n_subjects.max())}")
    ax2.scatter(cs.gz_body, cs["median"], s=30, color=SERIES[0], edgecolor=TOKENS["surface"], lw=1.5, zorder=3)
    a = anchors[(anchors.base == "ijv_area") & (anchors.lbnp_mmHg.fillna(0) == 0)]
    lee = a[(a.dataset == "lee2020_partial_gravity") & (a.environment == "parabolic_flight")]
    ax2.errorbar(lee.gz_body, lee.value, yerr=[lee.value - lee.ci_low, lee.ci_high - lee.value], fmt="o", ms=6,
                 color=SERIES[1], ecolor=SERIES[1], elinewidth=2, capsize=0, label="Parabolic flight 0.25–0.75 G (Lee 2020)")
    iss = a[a.environment.astype(str).str.startswith("iss")]
    ax2.errorbar(iss.gz_body + np.array([0.0, 0.04])[: len(iss)], iss.value, yerr=[iss.value - iss.ci_low, iss.ci_high - iss.value],
                 fmt="s", ms=6, color=SERIES[2], ecolor=SERIES[2], elinewidth=2, capsize=0, label="ISS 0 G, flight days 50/150")
    sup = a[a.condition == "preflight_supine"]
    ax2.errorbar(sup.gz_body - 0.04, sup.value, yerr=[sup.value - sup.ci_low, sup.ci_high - sup.value], fmt="s", ms=6,
                 mfc=TOKENS["surface"], color=TOKENS["ink2"], ecolor=TOKENS["ink2"], elinewidth=2, capsize=0,
                 label="Same crew lying flat on ground (1 G)")
    ax2.set_yscale("log")
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

    ax2.yaxis.set_major_locator(FixedLocator([10, 20, 50, 100, 200]))
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax2.yaxis.set_minor_locator(NullLocator())
    ax2.axvline(0, color=TOKENS["axis"], lw=1, zorder=0)
    ax2.set_xlabel("Head-to-foot gravity, gz_body [g]  (− head-down · + head-up)")
    ax2.set_ylabel("Jugular vein cross-section [mm²]")
    ax2.set_title("B · Physiology layer: neck veins fill as gravity falls")
    ax2.legend(loc="lower left", fontsize=8)
    _caption(fig, "Real data only. A: UBFC-rPPG DATASET 2 (Bobbia et al. 2019). B: Whittle & Diaz-Artiles 2023 (MIT), "
                  "Lee et al. 2020, Marshall-Goebel et al. 2019 (IJV side: tilt = L/R mean, Lee = right, ISS = left). "
                  "The two layers are validated separately; no dataset links them.")
    fig.tight_layout(rect=(0, 0.045, 1, 1))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300)
    plt.close(fig)
    return out


def fig_rppg_improvement(baseline_windows: pd.DataFrame, improved_windows: pd.DataFrame, out: Path) -> Path:
    """HOLDOUT half only: baseline POS vs improved track (± abstention), MAE and share of gross errors."""
    from vascushift.optical.improved import split_of

    plt = _style()
    b = baseline_windows[(baseline_windows.protocol == "w10s2") & (baseline_windows.method == "pos") & baseline_windows.included].copy()
    b["split"] = [split_of(s, sub) for s, sub in zip(b.session_id, b.subset)]
    b = b[b.split == "holdout"]
    i = improved_windows[improved_windows.included & (improved_windows.split == "holdout")]
    groups = [("Baseline\nPOS", b), ("Improved\n(ROI + tracking)", i), ("Improved\n+ abstain", i[~i.abstain])]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.2, 3.6))
    cols = [TOKENS["muted"], SERIES[0], SERIES[0]]
    for ax, fn, lab in ((ax1, lambda g: g.error_bpm.abs().mean(), "Mean absolute error [bpm]"),
                        (ax2, lambda g: (g.error_bpm.abs() > 10).mean() * 100, "Windows off by > 10 bpm [%]")):
        vals = [fn(g) for _, g in groups]
        bars = ax.bar(range(3), vals, width=0.5, color=cols, edgecolor=TOKENS["surface"])
        bars[2].set_alpha(0.55)
        for k, v in enumerate(vals):
            ax.text(k, v, f"{v:.2f}", ha="center", va="bottom", fontsize=9, color=TOKENS["ink"])
        ax.set_xticks(range(3), [g[0] for g in groups])
        ax.set_ylabel(lab)
        ax.grid(axis="x", visible=False)
        ax.set_ylim(0, max(vals) * 1.2)
        ax.set_axisbelow(True)
    kept = len(i[~i.abstain]) / len(i) * 100
    ax1.set_title("Held-out half of UBFC (29 recordings)")
    ax2.set_title(f"Abstain keeps {kept:.0f} % of windows")
    _caption(fig, "Real data. Variant chosen on the other half (TUNE) and checked here once. 10 s windows. "
                  "EXPERIMENTAL track; the frozen baseline is unchanged.")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out
