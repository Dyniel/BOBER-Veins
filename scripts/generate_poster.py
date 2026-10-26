#!/usr/bin/env python3
"""
Generates publication-ready 60 cm x 90 cm portrait scientific poster for ISSSP 2026.
Assembles scientific diagrams, formulas, tables, and results into a high-res poster graphic.
"""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.patches as patches

REPO_ROOT = Path(__file__).resolve().parent.parent
FIGS_DIR = REPO_ROOT / "reports" / "figures"


def generate_isssp_poster(output_path: str = "reports/figures/isssp_poster_60x90.png") -> None:
    # 60cm x 90cm is 2:3 aspect ratio. Size (14, 21) at 180 dpi gives ~2520 x 3780 pixels (<10MB)
    fig = plt.figure(figsize=(14, 21), dpi=180)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 21)

    # 1. Poster Background
    bg = patches.Rectangle((0, 0), 14, 21, fc="#f8fafc", ec="none")
    ax.add_patch(bg)

    # 2. Header Banner
    header = patches.Rectangle((0, 18.8), 14, 2.2, fc="#0f172a", ec="none")
    ax.add_patch(header)

    ax.text(0.7, 20.35, "ISSSP 2026 &middot; Hong Kong Finals", fontsize=12, fontweight="bold", color="#38bdf8", va="center")
    ax.text(0.7, 19.8, "BOBER Veins / VascuShift-GPINN", fontsize=24, fontweight="bold", color="#ffffff", va="center")
    ax.text(0.7, 19.25, "Physics-Informed Modeling of Gravity-Dependent Venous Hemodynamics & Optical rPPG", fontsize=13, color="#94a3b8", va="center")
    ax.text(13.3, 19.5, "Authors: Daniel, Natalia, Michał, Jakub\nSpace Medicine Payload Group", fontsize=10.5, color="#cbd5e1", ha="right", va="center")

    # Helper function for card panels
    def draw_card(x, y, w, h, title, title_color="#1e293b"):
        card = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15", ec="#cbd5e1", fc="#ffffff", lw=1.2)
        ax.add_patch(card)
        ax.text(x + 0.3, y + h - 0.4, title, fontsize=12, fontweight="bold", color=title_color, va="center")
        divider = patches.Rectangle((x + 0.3, y + h - 0.55), w - 0.6, 0.02, fc="#e2e8f0", ec="none")
        ax.add_patch(divider)

    # Panel 1: Scientific Motivation (Left column, y: 15.2 to 18.5)
    draw_card(0.6, 15.2, 6.0, 3.3, "1. SCIENTIFIC MOTIVATION & PROBLEM", "#0369a1")
    txt_p1 = (
        "• Cephalad Fluid Shift: Upright 1G posture produces a vertical hydrostatic drop\n"
        "  ΔPh = ρ·g·Δh ≈ 27.3 mmHg, keeping internal jugular veins (IJV) collapsed.\n"
        "• Microgravity (0G): Eliminates this column (ΔPh = 0), driving severe jugular\n"
        "  engorgement (+800% area) and elevated cervical venous pressure (21 mmHg).\n"
        "• SANS & Thrombosis: Persistent venous congestion impairs ocular and cranial\n"
        "  drainage, contributing to Spaceflight-Associated Neuro-ocular Syndrome\n"
        "  and documented cases of jugular venous blood flow stasis in astronauts.\n"
        "• Goal: Develop an interpretable physics-informed model and evaluate non-contact\n"
        "  optical rPPG feasibility for autonomous spaceflight health monitoring."
    )
    ax.text(0.9, 16.5, txt_p1, fontsize=9.2, color="#334155", va="center", linespacing=1.45)

    # Panel 2: Real ESA Data & Dose Response (Right column, y: 15.2 to 18.5)
    draw_card(7.4, 15.2, 6.0, 3.3, "2. REAL DATA: ESA 82nd PARABOLIC FLIGHT", "#0369a1")
    # Embed Fig 2
    fig2_path = FIGS_DIR / "fig2_gravity_physiology.png"
    if fig2_path.exists():
        im2 = mpimg.imread(str(fig2_path))
        ax.imshow(im2, extent=[7.6, 13.2, 15.4, 17.8], aspect="auto", zorder=3)

    # Panel 3: System Architecture & Boundaries (Full width, y: 11.5 to 14.9)
    draw_card(0.6, 11.5, 12.8, 3.4, "3. SYSTEM ARCHITECTURE & SCIENTIFIC BOUNDARIES", "#4338ca")
    fig1_path = FIGS_DIR / "fig1_architecture.png"
    if fig1_path.exists():
        im1 = mpimg.imread(str(fig1_path))
        ax.imshow(im1, extent=[0.8, 13.2, 11.7, 14.3], aspect="auto", zorder=3)

    # Panel 4: Physiological Model Comparison (Left column, y: 7.2 to 11.2)
    draw_card(0.6, 7.2, 6.0, 4.0, "4. RESULTS: LEAVE-ONE-SUBJECT-OUT CV", "#047857")
    fig3_path = FIGS_DIR / "fig3_baseline_comparison.png"
    if fig3_path.exists():
        im3 = mpimg.imread(str(fig3_path))
        ax.imshow(im3, extent=[0.8, 6.4, 7.4, 10.6], aspect="auto", zorder=3)

    # Panel 5: Optical rPPG Subsystem (Right column, y: 7.2 to 11.2)
    draw_card(7.4, 7.2, 6.0, 4.0, "5. RESULTS: OPTICAL rPPG BENCHMARK", "#b91c1c")
    fig5_path = FIGS_DIR / "fig5_rppg_validation.png"
    if fig5_path.exists():
        im5 = mpimg.imread(str(fig5_path))
        ax.imshow(im5, extent=[7.6, 13.2, 7.4, 10.6], aspect="auto", zorder=3)

    # Panel 6: Identifiability & Ablations (Left column, y: 3.2 to 6.9)
    draw_card(0.6, 3.2, 6.0, 3.7, "6. IDENTIFIABILITY & PHYSICS ABLATIONS", "#b45309")
    fig6_path = FIGS_DIR / "fig6_ablation_results.png"
    if fig6_path.exists():
        im6 = mpimg.imread(str(fig6_path))
        ax.imshow(im6, extent=[0.8, 6.4, 3.4, 6.3], aspect="auto", zorder=3)

    # Panel 7: Interactive Demonstrator & Future Work (Right column, y: 3.2 to 6.9)
    draw_card(7.4, 3.2, 6.0, 3.7, "7. DEMONSTRATOR & MISSION PAYLOAD", "#6b21a8")
    fig7_path = FIGS_DIR / "fig7_demonstrator.png"
    if fig7_path.exists():
        im7 = mpimg.imread(str(fig7_path))
        ax.imshow(im7, extent=[7.6, 13.2, 3.4, 6.3], aspect="auto", zorder=3)

    # Footer Bar
    footer = patches.Rectangle((0, 0), 14, 0.9, fc="#0f172a", ec="none")
    ax.add_patch(footer)
    ax.text(0.7, 0.45, "Open Source Scientific Code: https://github.com/Dyniel/BOBER-Veins &middot; DOI: 10.57780/esa-0ggni9p", fontsize=10, color="#94a3b8", va="center")
    ax.text(13.3, 0.45, "ISSSP 2026 &middot; Hong Kong Finals", fontsize=10, fontweight="bold", color="#38bdf8", ha="right", va="center")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=180)
    pdf_path = str(Path(output_path).with_suffix(".pdf"))
    plt.savefig(pdf_path)
    plt.close()
    print(f"Generated official 60x90cm poster at:\n  - {output_path}\n  - {pdf_path}")


if __name__ == "__main__":
    generate_isssp_poster()

