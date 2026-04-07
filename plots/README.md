# Plot Generation

This folder contains the reproducible plotting pipeline for the publication figures derived from the saved audit outputs.

## Figures

The generator produces three figures:

- a pooled PHM Society Conference + IJPHM figure for the main paper
- a PHM Society Conference figure for the appendix
- an IJPHM figure for the appendix

The figures intentionally use two different designs:

- Main-paper pooled figure:
  - one compact horizontal bar chart
  - strict public availability only, where "publicly available" means `A1`
  - four pooled categories across all PHM Society Conference + IJPHM papers from `2022-2025`:
    - `Both code and data publicly available`
    - `Only code publicly available`
    - `Only data publicly available`
    - `Neither publicly available`
- Appendix venue figures:
  - x-axis: publication year
  - two bars per year: `Code` and `Data`
  - each bar is a 100% stack of `A1` through `A5`

## Inputs

The generator reads yearly audit CSVs from:

- `data/processed/phm_society_conf/<year>/audit/audit_results.csv`
- `data/processed/ijphm/<year>/audit/audit_results.csv`

## Outputs

Generated files are written to `plots/output/`:

- `pooled_reproducibility_2022_2025.pdf`
- `pooled_reproducibility_2022_2025.png`
- `phm_society_conf_reproducibility_2022_2025.pdf`
- `phm_society_conf_reproducibility_2022_2025.png`
- `ijphm_reproducibility_2022_2025.pdf`
- `ijphm_reproducibility_2022_2025.png`
- `plot_data.csv`
- `pooled_overview_data.csv`

## Regeneration

Install plotting dependencies:

```bash
uv sync --extra plots
```

Generate the figures:

```bash
uv run python -m plots.build_audit_figures
```
