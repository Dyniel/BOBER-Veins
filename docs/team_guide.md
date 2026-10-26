# Team Guide & Module Ownership: BOBER Veins

## 1. Team Roster & Module Ownership (ISSSP 2026)

| Member | Role | Core Responsibilities | Key Files & Modules |
| :--- | :--- | :--- | :--- |
| **Daniel** | **Science Lead** | Overall hypothesis formulation, physiological interpretation, identifiability bounds, experimental methodology, competition pitch & presentation. | `docs/scientific_background.md`, `reports/isssp/work_report.md`, `reports/isssp/presentation_outline.md` |
| **Natalia** | **Data & Sensor Concept** | ESA HREDA data audit, data dictionary, schema validation, payload sensor concept, technical documentation. | `src/vascushift/data/esa_loader.py`, `src/vascushift/data/validation.py`, `docs/data_dictionary.md` |
| **Michał** | **Physics & AI** | Two-compartment lumped parameter simulator, inverse parameter estimation, PINN architecture, physics loss ablations, uncertainty analysis. | `src/vascushift/physics/`, `src/vascushift/models/`, `src/vascushift/experiments/ablations.py`, `src/vascushift/experiments/recovery.py` |
| **Jakub** | **Optical & Software** | rPPG pipeline, Green/CHROM/POS implementations, SNR & quality assessment, benchmarking, interactive demonstrator. | `src/vascushift/optical/`, `src/vascushift/experiments/rppg.py`, `demo/`, `src/vascushift/visualization/dashboard.py` |

---

## 2. Quickstart Guide for Collaborators

### Environment Setup:
```bash
git clone https://github.com/Dyniel/BOBER-Veins.git
cd BOBER-Veins
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Running Tests:
```bash
pytest tests/
```

### Standard Execution Commands:
```bash
# 1. Audit real ESA HREDA data availability and local files
python -m vascushift.cli data-audit --config configs/data.yaml

# 2. Run forward venous hemodynamic simulation across gravity levels
python -m vascushift.cli simulate --config configs/physics_model.yaml

# 3. Train and evaluate physics-informed model on verified ESA cohort
python -m vascushift.cli train-physics --config configs/physiology.yaml

# 4. Run optical rPPG algorithm benchmarks
python -m vascushift.cli run-rppg --config configs/rppg.yaml

# 5. Run full scientific evaluation (LOSO CV, ablations, identifiability)
python -m vascushift.cli evaluate --config configs/experiments.yaml

# 6. Generate all publication figures (Figures 1 - 7)
python -m vascushift.cli figures --config configs/experiments.yaml

# 7. Launch local interactive web demonstrator
python -m vascushift.cli demo --port 8501
```

