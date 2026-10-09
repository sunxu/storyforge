# StoryForge v0.1 Held-out Test — frozen evaluation evidence

- Evaluation Job: `6ac85c22fee2c90070172dad`
- Split: **test**, 20 story-isolated prompts; two anonymized responses per prompt, generated with max_new_tokens=1536, temperature=0
- Base: `Qwen/Qwen3.8-27B`; tuned arm: v0.1 checkpoint-9 QLoRA adapter
- Scope: publicly reproducible **retrospective evaluation evidence**, not a new untouched test set
- Training engineering: PASS; adapter quality promotion: **NOT APPROVED**

## Rounds (reported separately)

| Outcome | First round (g, q, c, ch + 4 arbitrations) | Second round (cp, ceh-fixed, ch + eval-012 arbitration) |
|---|---:|---:|
| Base sample wins | 13 | 10 |
| Adapter sample wins | 7 | 10 |
| Base raw preference votes | 44 | 34 |
| Adapter raw preference votes | 28 | 25 |
| Raw ties | 8 | 1 |

Second-round role of ch: **`reviewers/round2/ch.csv` comes from the distinctly uploaded `StoryForge_Reviewer_ch(1).csv`; `reviewers/round1/ch.csv` comes from `StoryForge_Reviewer_ch.csv`. They are NOT the same file.** Original and corrected ceh are also both preserved; only `ceh-fixed.csv` is counted in the second-round official calculation. For `eval-012`, fourth-party arbitration chooses anonymous A; the original cp=TIE / ceh=B / ch=A remains unchanged in the source files.

First-round q review contains known reasoning/sample misalignment issues; round-one original counts are preserved rather than silently invalidating them. Second-round ceh original 018/019 scores were transposed and corrected in `ceh-fixed.csv`. The audits document these issues.

## Directories

- `reviewers/`: original CSV evidence (4+4 files), including the uncorrected ceh
- `test/`: held-out prompts, blind output pairs, manifest and original answer key
- `arbitration/`: two independent arbitration reports (round 1 four contested cases and round 2 eval-012)
- `results/`: raw source-based unblinded summaries, retaining both inferential and original-key-verified files
- `reports/`: audit and interpretation; read with primary result JSON

## Provenance and integrity

`git-blobs.json` lists **Git blob SHA-1 for the original file bytes** (including BOM and CRLF where applicable), verified against local source file digests when uploading. The original answer key belongs to the test Job above and its exposure is deliberate, since these are closed evaluation rounds. This does not authorize uploading real passwords or access tokens.

**Important:** the v0.1 test outputs and their explanations have now been seen and used for error analysis; any training or checkpoint selection based on these examples requires a separate newly held-out story-level test before claiming future generalization. No data from this folder may be retroactively used as an untouched v0.1 validation set.
