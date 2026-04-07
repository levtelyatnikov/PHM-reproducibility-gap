# Validation

## Scope

The public audit in this repository covers:

- PHM Society Conference (`2022–2025`)
- IJPHM technical papers (`2022–2025`)

The validation workflow is built around the deterministic audit outputs, not around raw PDFs or private local corpora.

## Full-Text Rule

The final PHM/IJPHM labels are based on extracted full paper text.

Abstract-only evidence is insufficient for final artifact-sharing claims in these venues. This rule is enforced in the analysis-text selection path and surfaced in the outputs through:

- `analysis_text_source`
- `analysis_text_policy_passed`
- `analysis_text_policy_note`
- `repro_audit_eligible`

The repo also keeps a second, appendix-facing data-access signal:

- `data_public_external_dataset`
- `data_public_external_dataset_type`
- `data_public_external_dataset_note`

This signal is separate from `A1–A5`. It captures benchmark or externally public datasets without overstating strict reproducibility.

## Gold Set

Create the annotation template with:

```bash
uv run python -m scripts.prepare_gold_set --output data/validation/gold_set_template.csv
```

Default design:

- `80` papers total
- `10` PHM papers per year for `2022–2025`
- `10` IJPHM papers per year for `2022–2025`
- oversamples current positives and likely false-negative cases

The gold template includes:

- `paper_id`
- `source`
- `year`
- `title`
- predicted labels and notes
- blank `code_label_gold` and `data_label_gold`
- annotation and adjudication fields

## Evaluation

Run the evaluation once the gold labels are filled:

```bash
uv run python -m scripts.evaluate_2022 \
  --gold data/validation/gold_set_filled.csv \
  --predictions data/processed/audit_results.csv \
  --output-dir data/validation
```

This produces:

- `evaluation_summary.json`
- `evaluation_disagreements.csv`

The evaluation reports:

- code and data exact-match accuracy
- joint accuracy
- macro-F1 for code and data
- per-class precision, recall, and F1 for `A1–A5`
- confusion matrices
- strict `A1` precision and recall

## False-Negative Review

The highest-yield manual review target is the set of current `A5` papers whose traces still contain suspicious cues such as:

- `github`
- `gitlab`
- `zenodo`
- `figshare`
- `supplementary material`
- `dataset is available`
- `data available`
- `code and data available`
- `repository`
- `available online`

When a real miss is found, tag the failure mode before changing any rule:

- `mixed_code_data_sentence`
- `supplementary_material_release`
- `ownership_phrase_missing`
- `public_benchmark_only`
- `reference_section_false_positive`
- `not_a_real_artifact_release`

Only update the analyzer when the miss is systematic.

## Recommended Taxonomy

For the paper, the strongest framing is:

- keep `A1–A5` strict and artifact-oriented
- do not add public benchmark use as a sixth label in the same axis
- report benchmark and external-public-dataset usage as a separate appendix dimension

Why this is preferred:

- a public benchmark does not imply an author-released artifact
- a public dataset does not imply that preprocessing, splits, or evaluation boundaries are reproducible
- folding benchmark usage directly into `A2` inflates data accessibility in a way that weakens the paper's main reproducibility claim

The manual PHM and IJPHM spot checks are intended to support exactly this distinction.

## Real-Case Regression Suite

The repo already includes real-paper regression cases in:

- [/Users/leone/projects/PHM_paper_parser/tests/engine/test_real_pdf_cases.py](/Users/leone/projects/PHM_paper_parser/tests/engine/test_real_pdf_cases.py)

The suite is intended to keep common failure modes fixed over time:

- benchmark mentions that should stay non-`A1`
- on-request and unavailable data statements
- mixed code/data wording
- reference-only GitHub mentions

## Appendix Benchmark Tables

Build appendix-ready benchmark tables with:

```bash
uv run python -m scripts.build_appendix_tables
```

This writes:

- `data/processed/appendix/benchmark_summary_by_source.csv`
- `data/processed/appendix/benchmark_summary_by_year.csv`
- `data/processed/appendix/benchmark_name_frequency.csv`

These tables are intentionally separate from the strict `A1` reproducibility claims.
