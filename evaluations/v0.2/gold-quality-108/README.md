# StoryForge v0.2 — 108 Gold-quality candidates (stories 06–15)

**Owner decision (2026-10-13): keep exactly the 108 original-text candidates for which independent Reviewer 1 and Reviewer 2 both returned ACCEPT.** Do not promote any adjudication-only acceptance or disagreements.

## Admission states

- Curator quality status: `GOLD_QUALITY_ACCEPTED_BY_OWNER` (108 records).
- Formal training admission: **`PENDING_NOT_APPROVED`**. This is NOT a training-ready `train.jsonl` file.
- No train/validation/test split (`split=null`); no GPU job, Hugging Face upload, data transformation or training was approved by this selection.
- The first batch `../gold-quality-87/` remains a separate, unchanged 87-record snapshot. The two curator-quality cohorts total 195; they are **not** a single training dataset.

## Included original records

| Story | Double ACCEPT |
|---|---:|
| 06 | 7 |
| 07 | 0 |
| 08 | 4 |
| 09 | 25 |
| 10 | 19 |
| 11 | 0 |
| 12 | 4 |
| 13 | 17 |
| 14 | 12 |
| 15 | 20 |
| **Total** | **108** |

From the frozen pool of 150, there were 108 ACCEPT/ACCEPT, 30 ACCEPT/HOLD or HOLD/ACCEPT, 4 ACCEPT/REJECT or REJECT/ACCEPT, 4 HOLD/HOLD and 4 REJECT/REJECT. The remaining **42 records are NOT_SELECTED_THIS_RELEASE**. The additional six quality approvals from the later administrator arbitration are intentionally excluded.

## Files and provenance

- `gold_quality_accepted_108.jsonl`: **byte-exact original record lines** extracted from the frozen 150 records, in the frozen double-ACCEPT selection order. Original messages and metadata are unchanged.
- `gold_108_index.csv`: anonymized blind ID, original candidate ID, source target SHA256, source story, both reviewer decisions and five-dimensional scores. Index contains derived metadata only.
- `other_42_not_selected.csv`: identifiers and review statuses for nonselected records, without their target response bodies.
- `dual_accept_review_evidence_108.jsonl`: evidence excerpts and rationale for only the 108 selected candidates; does not substitute for the original blind bundles.
- `selection_manifest.json`: source identifiers, SHA256 and Git blob integrity, selection policy, review counts and gates.
- `verification_report.json`: machine-readable precommit verification status.
- `verify_gold108.py`: read-only dataset/index/exclusion and optional frozen-source byte-line verifier.

Frozen 150-row source `StoryForge_v02_06-15_R04_Delivery_20261012.zip/gold_selected.jsonl` has SHA256 `8fbd2581b6823882d27e7839238335319202b1d9a726fc25d9aa74fedf5487f1`. The selected 108-row JSONL has SHA256 `27d15b6f8baf7935ee2c48f85558adc3b5b25e3558e127485d0f17b620f80308`.

## Not yet cleared

Full character cards at the target point in time; long-term canon; participant age, consent and content boundaries; 04↔07 story-isolation check; v0.1 split/held-out overlap; pinned Qwen 16,384-token verification; actual last-round Assistant-only loss masking. Do not treat historical Assistant messages in the sample context as supervised labels. The frozen source conversation archives are not added by this commit.

**No original sample text is rewritten and the existing v0.1 freeze tag is untouched.**
