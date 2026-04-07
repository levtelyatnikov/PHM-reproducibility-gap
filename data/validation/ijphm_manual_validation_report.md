# IJPHM Manual Validation Report

## Scope

This report summarizes a manual validation pass over a reproducible `60`-paper IJPHM sample:

- `15` papers from `2022`
- `15` papers from `2023`
- `15` papers from `2024`
- `15` papers from `2025`

Artifacts:

- [data/validation/ijphm_manual_validation_sample.csv](data/validation/ijphm_manual_validation_sample.csv)
- [data/validation/ijphm_manual_validation_snippets.csv](data/validation/ijphm_manual_validation_snippets.csv)
- [data/validation/ijphm_manual_validation_gold.csv](data/validation/ijphm_manual_validation_gold.csv)
- [data/validation/ijphm_manual_validation_eval/evaluation_summary.json](data/validation/ijphm_manual_validation_eval/evaluation_summary.json)
- [data/validation/ijphm_manual_validation_eval/evaluation_disagreements.csv](data/validation/ijphm_manual_validation_eval/evaluation_disagreements.csv)

## Current Strict-Label Results

After the latest analyzer fixes, the strict IJPHM sample matches the manual gold set exactly:

- code accuracy: `60/60 = 100.0%`
- data accuracy: `60/60 = 100.0%`
- joint accuracy: `60/60 = 100.0%`

The remaining macro-F1 values are depressed by class imbalance in this small sample, not by observed disagreement:

- code macro-F1: `0.600`
- data macro-F1: `0.600`

Strict `A1` precision in the sample remains:

- code `A1` precision: `1.000`
- data `A1` precision: `0.000`

The `data A1` precision is `0.000` because the manual sample contains no `data=A1` cases.

## Patterns Found And Fixed

The manual IJPHM pass surfaced four concrete rule classes:

1. Direct repository links can appear in non-standard forms.
   - `www.github...` without an explicit scheme
   - public Google Drive repository folders

2. Reference sections can contain GitHub links that are not artifact releases.
   - these must not become `code=A2`

3. Generic system-design language can trigger false positives.
   - phrases like `data exchange ... upon request` are not data-sharing statements

4. Dataset papers can make owned public-access claims without a direct link.
   - these belong in `A2`, not `A5`

These patterns are now covered by regression tests in [tests/engine/test_rules.py](tests/engine/test_rules.py).

## Recommendation For The Paper

The IJPHM manual pass reinforces the same methodological conclusion as the PHM spot check:

- keep `A1–A5` strict and artifact-oriented
- do not fold public benchmark use directly into the main `A1–A5` axis
- report benchmark or externally public dataset usage as a separate appendix dimension

This repo now exposes that second dimension through:

- `data_public_external_dataset`
- `data_public_external_dataset_type`
- `data_public_external_dataset_note`

This keeps the main reproducibility claim conservative while still documenting broader data accessibility patterns.
