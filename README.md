# PHM Reproducibility Audit

This repository audits reproducibility signals in two PHM publication venues:

- PHM Society Conference papers (`2022–2025`)
- IJPHM technical papers (`2022–2025`)

The published statistics use a strict definition of public availability:

- `A1`: a directly accessible, author-controlled code or data artifact

The final PHM and IJPHM labels are computed from extracted full paper text, not from abstracts alone.

The repository also publishes a separate appendix-facing signal for externally public datasets and benchmarks. This is tracked independently from `A1–A5` so public benchmark use does not get confused with author-released artifacts.

## Repository Scope

The public repository is designed for inspection and regeneration of processed outputs.

Included:

- parsers and analyzer code
- processed CSV/JSON outputs
- plotting scripts and generated figures
- paper-facing `.tex` sections
- validation scaffolding, regression tests, and gold-set templates

Excluded from publication:

- raw downloaded PDFs
- extracted full-text corpora
- article HTML dumps
- credentials, API keys, and user emails

## Quick Start

Create the environment and run the deterministic audit rebuild from local raw corpora:

```bash
uv sync --extra pdf --extra plots --extra dev
uv run python -m scripts.bootstrap_2022 --sources phm,ijphm --from-raw --skip-llm --config config/pilot_2022.yaml
```

Regenerate the figures:

```bash
uv run python -m plots.build_audit_figures
```

Build benchmark appendix tables:

```bash
uv run python -m scripts.build_appendix_tables
```

Build the standalone audit report in this repo:

```bash
cd paper
make report
```

This regenerates the validation summary, appendix tables, and paper-export macros/tables before compiling `paper/build/report.pdf`. To force a full refresh of the generated figures as well, run:

```bash
cd paper
make refresh
make report
```

Prepare the manual gold-set template:

```bash
uv run python -m scripts.prepare_gold_set --output data/validation/gold_set_template.csv
```

## Corpus and Denominators

- PHM Society Conference:
  - `2022`: `Technical Research Papers`
  - `2023–2025`: `Technical Research Papers` and `Industry Experience Papers`
- IJPHM:
  - `Technical Papers` only
  - `Technical Briefs` excluded from the audited denominator

## How To Inspect One Paper

The main inspection file is the yearly `audit_trace.csv`. Each row includes:

- `code_label` and `data_label`
- one-hot `A1–A5` flags
- `code_note` and `data_note`
- supporting URL fields
- `analysis_text_source`
- `analysis_text_policy_passed`
- `evidence_pointer`
- benchmark flags for appendix-only analysis
- external-public-dataset flags for appendix-only analysis

Start with:

- [/Users/leone/projects/PHM_paper_parser/data/processed/phm_society_conf/2022/audit/audit_trace.csv](/Users/leone/projects/PHM_paper_parser/data/processed/phm_society_conf/2022/audit/audit_trace.csv)
- [/Users/leone/projects/PHM_paper_parser/data/processed/ijphm/2025/audit/audit_trace.csv](/Users/leone/projects/PHM_paper_parser/data/processed/ijphm/2025/audit/audit_trace.csv)

## Main Outputs

Per-year processed outputs are committed under:

- [/Users/leone/projects/PHM_paper_parser/data/processed/phm_society_conf](/Users/leone/projects/PHM_paper_parser/data/processed/phm_society_conf)
- [/Users/leone/projects/PHM_paper_parser/data/processed/ijphm](/Users/leone/projects/PHM_paper_parser/data/processed/ijphm)

Each yearly audit bundle contains:

- `audit_results.csv`
- `audit_trace.csv`
- `manual_review_queue.csv`
- `paper_manifest.csv`
- `summary.json`
- `papers.jsonl`

The pooled main-paper figure is:

- [/Users/leone/projects/PHM_paper_parser/plots/output/pooled_reproducibility_2022_2025.pdf](/Users/leone/projects/PHM_paper_parser/plots/output/pooled_reproducibility_2022_2025.pdf)

## Limitations

- The audit is conservative by design and prioritizes precision for strict `A1`.
- Named public benchmark reuse is tracked separately and does not upgrade a paper to `A1`.
- Externally public datasets are tracked separately and do not automatically change the strict `A1–A5` label.
- The public repository publishes processed evidence logs, not copyrighted raw corpora.
- A small number of papers remain non-eligible because usable extracted full text was not recovered.

See [/Users/leone/projects/PHM_paper_parser/ANALYZER.md](/Users/leone/projects/PHM_paper_parser/ANALYZER.md) for the labeling logic and [/Users/leone/projects/PHM_paper_parser/VALIDATION.md](/Users/leone/projects/PHM_paper_parser/VALIDATION.md) for the validation workflow.
