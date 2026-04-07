# Reproducibility Figures Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a reproducible plotting pipeline that generates publication-ready PHM Society Conference, IJPHM, and pooled PHM+IJPHM reproducibility figures from the saved audit CSVs.

**Architecture:** Read yearly `audit_results.csv` files from the processed audit folders, aggregate category proportions for `code_label` and `data_label`, and render a consistent 100% stacked-bar figure design for the pooled main-paper plot plus venue-specific appendix plots. Save vector and raster outputs in a dedicated `plots/` folder with a single entrypoint script and deterministic styling.

**Tech Stack:** Python 3.11+, matplotlib, csv/stdlib data loading, pytest.

---

### Task 1: Add plotting dependency and scaffold the plots folder

**Files:**
- Modify: `pyproject.toml`
- Create: `plots/__init__.py`
- Create: `plots/README.md`

**Step 1: Write minimal dependency/config changes**

- Add a lightweight plotting extra using `matplotlib`.
- Create a new `plots/` package so the figure code is importable and testable.
- Document expected inputs and generated outputs in `plots/README.md`.

**Step 2: Run environment sync**

Run: `uv sync --extra plots`

Expected: matplotlib becomes available in the local environment.

### Task 2: Write failing aggregation tests

**Files:**
- Create: `tests/plots/test_build_audit_figures.py`

**Step 1: Write failing tests**

- Test pooling logic across PHM Society Conference and IJPHM yearly CSVs.
- Test that venue-specific aggregation preserves yearly `A1–A5` proportions for code and data.
- Test that the plotting entrypoint writes the three expected figure files and a plot-data CSV.

**Step 2: Run tests to verify failure**

Run: `uv run pytest tests/plots/test_build_audit_figures.py -q`

Expected: FAIL because the plotting module does not exist yet.

### Task 3: Implement aggregation and figure rendering

**Files:**
- Create: `plots/build_audit_figures.py`

**Step 1: Implement minimal plotting pipeline**

- Load `audit_results.csv` files for:
  - `data/processed/phm_society_conf/<year>/audit`
  - `data/processed/ijphm/<year>/audit`
- Aggregate code/data category counts into proportions.
- Render:
  - pooled PHM+IJPHM figure for the main paper
  - PHM Society Conference-only appendix figure
  - IJPHM-only appendix figure
- Save both `.pdf` and `.png` outputs plus a `plot_data.csv` artifact.

**Step 2: Run focused tests**

Run: `uv run pytest tests/plots/test_build_audit_figures.py -q`

Expected: PASS.

### Task 4: Generate real figures from the saved audit corpus

**Files:**
- Write outputs under: `plots/output/`

**Step 1: Run the plot generator**

Run: `uv run python -m plots.build_audit_figures`

Expected outputs:
- `plots/output/pooled_reproducibility_2022_2025.pdf`
- `plots/output/phm_society_conf_reproducibility_2022_2025.pdf`
- `plots/output/ijphm_reproducibility_2022_2025.pdf`
- PNG counterparts
- `plots/output/plot_data.csv`

### Task 5: Verify and document

**Files:**
- Update: `plots/README.md`

**Step 1: Verify**

Run: `uv run pytest -q`

Expected: PASS.

**Step 2: Document**

- Record the exact command used to regenerate figures.
- Briefly describe the semantics of the pooled main figure and the two appendix figures.
