# Analyzer

## Scope

This analyzer audits reproducibility signals in:

- PHM Society Conference papers
- IJPHM technical papers

It assigns two independent labels per paper:

- `code_label`
- `data_label`

Each label is one of:

- `A1`: directly accessible, author-controlled artifact
- `A2`: publicly claimed, but not backed by a verifiable owned link
- `A3`: restricted, such as available on request
- `A4`: explicitly unavailable
- `A5`: not mentioned

The audit is conservative. It is designed to minimize false-positive `A1` calls.

The repo now tracks two distinct notions of data accessibility:

- strict artifact-sharing labels (`A1–A5`)
- a separate external-public-data signal for benchmark or publicly accessible third-party datasets

This separation is intentional. Public benchmark usage can support partial reproducibility, but it does not imply that the paper's full methodology or preprocessing pipeline is reproducible.

## Core Policy

The final PHM and IJPHM labels are computed from extracted full paper text, not from abstracts alone.

That means:

- if extracted full text exists, the analyzer must use it
- abstract-only evidence is not sufficient for final PHM/IJPHM statistics
- papers without usable extracted full text are marked explicitly and excluded from strong reproducibility claims

This policy is enforced centrally in [`scripts/bootstrap_2022.py`](scripts/bootstrap_2022.py) through the analysis-text selection path.

The relevant output fields are:

- `analysis_text_source`
- `analysis_text_policy_passed`
- `analysis_text_policy_note`
- `repro_audit_eligible`

## Pipeline

The main flow is:

1. Parse venue issue and article pages.
2. Download the paper PDF when available.
3. Extract text from the PDF with PyMuPDF first, then `pdfplumber` and `pypdf` fallbacks.
4. Select the analysis text with a full-text-first policy.
5. Build evidence windows around URLs and availability statements.
6. Classify `code` and `data` separately with deterministic rules in [`engine/rules.py`](engine/rules.py).
7. Optionally send the same evidence to a three-judge OpenRouter ensemble.
8. Merge deterministic and judge outputs in [`engine/consensus.py`](engine/consensus.py).
9. Write paper-level outputs to `audit_results.csv`, `audit_trace.csv`, and `manual_review_queue.csv`.

## Deterministic Rules

The rules engine looks at code and data independently.

Typical code cues:

- `code`
- `repository`
- `repo`
- `implementation`
- `software`
- `package`
- `github`
- `gitlab`

Typical data cues:

- `dataset`
- `data set`
- `data`
- `benchmark`
- `corpus`
- `labels`
- `supplementary material`

The analyzer ranks candidate sentences and writes the strongest supporting sentence into the CSV note fields:

- `code_note`
- `data_note`
- `note`

These note fields are meant for manual spot checks, not just for debugging.

## A1 Through A5 Logic

### A1

`A1` requires both:

- a directly accessible artifact link
- ownership or release language close to that link

Examples:

- `our code is available at ...`
- `the framework is available at ...`
- `we release the dataset at ...`

### A2

`A2` captures public-availability claims without a verifiable owned link.

Examples:

- `publicly available`
- `open source`
- `available online`

### A3

`A3` captures restricted availability.

Examples:

- `available on request`
- `available upon reasonable request`
- `shared with researchers upon request`

### A4

`A4` captures explicit unavailability.

Examples:

- `not publicly available`
- `cannot be shared`
- `confidential dataset`

### A5

`A5` means no credible sharing statement was found for that channel after filtering.

## What The Analyzer Intentionally Suppresses

The analyzer does not treat these as `A1`:

- generic library links such as PyTorch, TensorFlow, or scikit-learn
- benchmark mentions without an owned artifact release
- bibliographic references that happen to contain GitHub links

This is why a paper can use a public benchmark and still remain `A5` for data sharing.

## Named Public Benchmark Signal

Named benchmark reuse is tracked separately from the strict `A1–A5` labels.

The audit exports:

- `data_named_public_benchmark`
- `data_public_benchmark_name`
- `data_public_benchmark_note`
- `data_public_external_dataset`
- `data_public_external_dataset_type`
- `data_public_external_dataset_note`

This appendix-oriented signal is for cases such as:

- `C-MAPSS`
- `CWRU`
- `IMS`
- `CALCE`
- `PRONOSTIA`

Benchmark reuse does not imply artifact release and never upgrades a paper to `A1`.

The broader external-public-data signal is the recommended appendix-facing way to report:

- named benchmark usage
- use of externally public datasets or repositories
- dataset papers that claim open access without a direct artifact link

This signal is intentionally orthogonal to the strict `A1–A5` labels.

## Outputs

The main outputs are:

- [data/processed/audit_results.csv](data/processed/audit_results.csv)
- [data/processed/audit_trace.csv](data/processed/audit_trace.csv)
- [data/processed/manual_review_queue.csv](data/processed/manual_review_queue.csv)

Per-year bundles are written under:

- [data/processed/phm_society_conf](data/processed/phm_society_conf)
- [data/processed/ijphm](data/processed/ijphm)

## Real-Case Regression Suite

The real-PDF regression suite is in:

- [tests/engine/test_real_pdf_cases.py](tests/engine/test_real_pdf_cases.py)

It includes real PHM papers spanning all five categories and protects against regressions such as:

- false `A1` calls from reference-only GitHub mentions
- missed supplementary-material releases
- missed mixed code/data availability sentences
- benchmark mentions being confused with owned releases

## Validation Workflow

The validation package lives alongside the code and processed outputs:

- gold-set template generation
- evaluation metrics and disagreement export
- benchmark appendix tables

See [VALIDATION.md](VALIDATION.md) for the validation protocol.
