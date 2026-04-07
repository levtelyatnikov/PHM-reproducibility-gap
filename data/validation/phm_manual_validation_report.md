# PHM Manual Validation Report

## Scope

This report documents a manual validation pass over a reproducible sample of PHM Society Conference papers from `2022–2025`.

- venue: PHM Society Conference
- scope: paper tracks only
- sample size: `60` papers
- sampling rule: `15` papers per year
- sampling seed: `20260407`

The sampled rows are stored in:

- [/Users/leone/projects/PHM_paper_parser/data/validation/phm_manual_validation_sample.csv](/Users/leone/projects/PHM_paper_parser/data/validation/phm_manual_validation_sample.csv)
- [/Users/leone/projects/PHM_paper_parser/data/validation/phm_manual_validation_snippets.csv](/Users/leone/projects/PHM_paper_parser/data/validation/phm_manual_validation_snippets.csv)
- [/Users/leone/projects/PHM_paper_parser/data/validation/phm_manual_validation_gold.csv](/Users/leone/projects/PHM_paper_parser/data/validation/phm_manual_validation_gold.csv)

The comparison against the current analyzer output is stored in:

- [/Users/leone/projects/PHM_paper_parser/data/validation/phm_manual_validation_eval/evaluation_summary.json](/Users/leone/projects/PHM_paper_parser/data/validation/phm_manual_validation_eval/evaluation_summary.json)
- [/Users/leone/projects/PHM_paper_parser/data/validation/phm_manual_validation_eval/evaluation_disagreements.csv](/Users/leone/projects/PHM_paper_parser/data/validation/phm_manual_validation_eval/evaluation_disagreements.csv)

## Manual Policy And Current Interpretation

The original PHM manual pass was intentionally broader than the final paper policy. It treated clearly identifiable public benchmark datasets as `A2` when the paper explicitly named or referenced them as public inputs, even when the dataset was not author-hosted.

For the publish-ready audit, this broader interpretation is retained only as a **sensitivity view**. The official repository outputs now use:

- strict `A1–A5` labels for artifact release
- a separate appendix-facing signal for `data_public_external_dataset`

So this PHM validation pass should now be read in two layers:

- strict layer:
  - the analyzer's direct-release calls, especially `A1`, are the official result
- sensitivity layer:
  - the manual pass highlights broader public-data-access cases that do not imply author-released reproducible artifacts

## Summary Metrics

Manual sample size:

- `60` papers total
- `15` papers from each of `2022`, `2023`, `2024`, and `2025`

Agreement with the current deterministic analyzer:

- code accuracy: `59/60 = 98.3%`
- data accuracy: `48/60 = 80.0%`
- joint code+data accuracy: `48/60 = 80.0%`
- code `A1` precision: `1.00`
- data `A1` precision: `1.00`

Per-year agreement:

- `2022`: code `15/15`, data `13/15`, joint `13/15`
- `2023`: code `15/15`, data `11/15`, joint `11/15`
- `2024`: code `15/15`, data `11/15`, joint `11/15`
- `2025`: code `14/15`, data `13/15`, joint `13/15`

## Main Finding

The disagreement pattern is concentrated in broader public-data-access sensitivity cases, not in strict `A1` release detection.

Across the `60` manually reviewed papers:

- there were `12` disagreements total
- `11` of the `12` disagreements were data-only misses where the analyzer predicted `A5` but the broader manual sensitivity pass assigned `A2`
- the remaining disagreement was a mixed case where the analyzer assigned `code = A2, data = A5`, while the manual review assigned `code = A5, data = A2`

The common failure mode is:

- the paper uses or explicitly points to a known public benchmark dataset
- the strict analyzer correctly avoids upgrading that statement into a direct artifact-release claim
- the result is `A5` in the official audit, while the broader manual sensitivity pass records it as public-data access

## Representative Disagreements

Examples from the sampled set:

- `phm-2022-3238`: manual `data = A2`
  - reason: the paper points to the NASA Prognostics Data Repository
- `phm-2022-3241`: manual `data = A2`
  - reason: the paper states that the maintenance-work-order dataset is open source
- `phm-2023-3572`: manual `data = A2`
  - reason: the study is evaluated on the N-CMAPSS DS02 benchmark dataset
- `phm-2023-3506`: manual `data = A2`
  - reason: the paper explicitly says it uses the NASA battery dataset
- `phm-2024-4145`: manual `data = A2`
  - reason: the paper states that the experiments use the C-MAPSS benchmark dataset
- `phm-2024-3903`: manual `data = A2`
  - reason: the paper explicitly evaluates on the publicly available VDAO dataset
- `phm-2025-4360`: manual `code = A5`, `data = A2`
  - reason: the analyzer appears to misfire on code, while the paper clearly states that it uses the publicly available XJTU-SY bearing dataset
- `phm-2025-4380`: manual `code = A3`, `data = A2`
  - reason: code is available on request, and the paper uses the IMS bearing benchmark dataset

## Interpretation

The current analyzer is strong for:

- strict `A1` calls
- explicit `A3` and `A4` data statements
- code classification in general

The current analyzer is intentionally conservative about:

- benchmark-style public data access
- explicit public-dataset reuse that does not amount to author-released reproducible artifacts

So the PHM paper-track outputs appear reliable for strict public release claims, while the separate appendix-facing external-public-data signal is the right place to discuss broader dataset accessibility.

## Implication For The Paper

This manual validation supports two separate reporting layers:

- Main text:
  - keep the strict public-release figure focused on direct code/data release
- Appendix:
  - report broader benchmark/public-dataset usage separately
  - state explicitly that public benchmark reuse does not imply precise methodological reproducibility
  - use this PHM manual pass as a sensitivity analysis rather than as a replacement for the strict audit
