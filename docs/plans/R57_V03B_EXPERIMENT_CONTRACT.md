# StoryForge R57-B — v0.3-B Data-Fix experiment contract (DRAFT; no training)

**Date:** 2026-10-26. **Branch:** `r57/v03b-data-design`. **State:** `R57B_DESIGN_PREPARED__OWNER_EXPERIMENT_SIGNOFF_PENDING__NO_GPU__NO_R50`.

## 0. Naming collision and authority

The historical `docs/plans/StoryForge_v03_Test_and_Training_Gates_20261014.json` assigns phase **R57** to promotion-or-HOLD after R56; the October plan also calls prompt-only ablation **v0.3-B**. This new initiative is explicitly **R57-B / `v0.3-B-datafix` design** to avoid silently overwriting those definitions. It does **not** close the original R57 release phase or claim the old formal evaluation was run. The title and proposal remain subject to Owner acceptance.

**No authorization** is conferred for GPU billing, CPU Hugging Face jobs, training, R50 disclosure, inference on protected prompts, model advancement, data release or semantic-owner signoff.

## 1. Frozen baselines and why a repair is proposed

- Qwen base revision `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
- Existing comparison adapter: **R46 v0.2 checkpoint-7**, reported SHA256 `bec4ba74d858db3ff117d581478ef9cac41b1ecc7ea2a67523f6db1096addf2b`. Preserve this baseline.
- R54 v0.3-A checkpoint-16, reported SHA256 `121ec8f70e66089c7c891a7052c6085de93824776aaa9a25295f612b269b60c0`; **NO-GO / NOT_PROMOTED**.
- R55 Gold5 v2 exposed 20 developer prompts from 2 worlds. Direct Pair gave 10:10 v0.2 vs R54 case majorities; six-axis means 3.363889 (R46) versus 3.216667 (R54). Review cannot establish generalization or decide a fresh final-model release.
- Owner-local all152 format check passed on 76 originally flagged candidate replies: 79 AI-assisted `CONFIRMED` category decisions, 69 `REJECTED`, 4 `HOLD`; *semantic certification remains pending*. Do not import the decisions as ground truth training labels. The separate 62 proposed hard-rule subtype tags are **diagnostic**, not an accepted corpus.
- Genuine historical completed SFT counts: v0.1 65 Train/15 Val; R46 49/15; R54 31/9. Of R54's 31 train target hashes, 14 matched R46 Train, 9 matched R46 Val and 8 matched neither; comprehensive three-run input-level lineage comparison still pending. A prior validation example later being used for training is not necessarily contamination of that earlier experiment; it must be disclosed, and may no longer be a clean comparison for a later experiment.
- Gold195: 87+108 frozen targets across 13 story UUIDs, **candidate pool only**. Do not translate accepted historical Gold automatically into accepted Dataset v0.4.

## 2. Three preregistered experiments (choose one first)

| ID | Change versus frozen R46/deployment contract | Intended inference |
|---|---|---|
| `B_PROMPT` | **Only** System/role-card packaging or story-specific rules prompt; same R46 adapter, same inputs and decoding | Can prompting alone address explicit rule failures? |
| `B_DATAFIX` | Same model revision, prompt/deployment contract, trainer implementation, optimizer setup and inference parameters; **only admitted training/validation dataset changes** | Can better supervised targets improve rule adherence without literary regression? |
| `B_COMBINATION` | Prompt and data changes, only after isolated prompt/data estimates exist | Separate interaction test, not a one-factor causal claim |

Default preparation track is **`B_DATAFIX`**, but **not** a paid training approval. Dataset size and world composition vary with data; changes must be declared because sample count/optimizer steps can affect interpretation. If R46 recipe cannot be exactly reproduced, preregister unavoidable deviations and change interpretation to exploratory.

The old R46 recipe reference (proposed lock, requires actual config cross-check): ms-swift 4.5.3, transformers 5.16.1; QLoRA NF4/bf16, rank64, alpha128, dropout0.05, all-linear; max_length 16384, last Assistant-only loss, batch1, grad accumulation8, lr 5e-5, one epoch. Never claim these are fully identical until source checkpoints/configs and optimizer steps are compared.

## 3. Data objective: literature quality while eliminating avoidable rule failures

**Initial quota for candidate discovery, not an enforced finished-sample distribution:** natural narrative ~50%, player agency/ghostwriting boundary ~25%, story-specific hard rules ~15%, identity/timeline ~10%. Multi-label every sample; an excellent narrative target can satisfy multiple categories simultaneously. Do not over-represent contrived refusals or deplete NPC initiative.

- `player_psychology_or_intent` and `player_action_or_speech`: don't attribute player intention/decisions or critical moves not in history; NPC can take its own actions.
- `user_event_continuity`: preserve user-established events.
- `forbidden_phrase_exact`, `forbidden_phrase_semantic`, `forbidden_user_echo`, `forbidden_echo_question`: obey **specific visible story rules**; semantic boundaries require independent case review.
- `dialogue_language_format`: per-world bilingual requirement, not a global instruction.
- `character_identity_or_relation`, `world_timeline_age`: cite source-at-target-time world/character information. Later export card is not automatic retroactive evidence.
- One assistant target is supervised; previous turns, System and User messages have masked loss. Never train on R55 preferred/failed candidates or R50 answers without separately justified data provenance and evaluation-exposure policy.

## 4. Dataset v0.4 intake / admission

**First batch:** manually sample 40–60 distinct candidate rows across eligible training worlds from Gold195 and/or separately verified new original sources; 120–160 admitted targets remains an *aspirational maximum-phase objective*, never a quota. No candidate is admitted merely due to Gold naming. No world is admitted by UUID-only comparison. 

Every private row uses `evaluations/v0.3/r57/R57_DATASET_V04_ADMISSION_SCHEMA.json` and the offline verifier. Record parent target SHA, exact prior train/val/dev exposure status, source-at-target-time canon, owner attestation and case-specific safety/age/consent evidence, full runtime-visible history availability, alias-connected world group, original versus synthetic/derived mode, and outcome from two individually distinguishable, evidence-anchored reviews. Owner makes a distinct final approval. Reviewer identity and independence are *recorded claims*, not technically proven by a schema.

`ACCEPTED_FOR_DATASET_V04` requires complete evidence and only `TRAIN`/`VALIDATION` eligible world components, no HOLD, no R50/body access and no protected-test exposure. Any `UNKNOWN`, `HOLD`, `EXPOSED` relevant to protected evaluation or train/val eligibility blocks acceptance; route uncertain cases to `HOLD` with reason. Derived edits preserve immutable parent source + revision diff provenance. Synthetic examples must have explicit origin and cannot be mislabeled original canonical Gold. Keep diagnostic negatives in a separate corpus, **not** SFT targets. Maintain potential R45 historical HOLD separately.

**World isolation:** all connected aliases/personae and semantic cross-story components must stay in one split. No Train/Val inter-component overlap or protected-test intersection. Freeze a private world-component graph and a count-only public report. Reviewer/test leakage and exact/near-duplicate target/history exposures must be audited before admission; hashing only gives exact-match evidence.

## 5. Gates, prior to asking for paid GPU

1. `R57B_PLAN_FROZEN`: Owner accepts exactly one initial arm, baseline/prompt/config, dataset construction rules, evaluation sizes and protocol.
2. `V04_SOURCE_AUDIT_PASS`: 40–60 source-based sampled candidates (or honestly fewer); hashed provenance/source-at-target-time, rights/boundaries and exposure screening documented.
3. `V04_ADMISSION_PASS`: every accepted target has two source-grounded reviews, explicit owner signoff, age/consent risk resolution, no protected exposure, reproducible derivation and no dataset leakage; disputed ones held out.
4. `V04_WORLD_SPLIT_PASS`: connected components assigned consistently, no overlap with future heldout; validator fail-closed.
5. `V04_CPU_COLLATOR_PASS`: actual pinned template/collator, full target hashes, attention context, last Assistant-only loss masking, length tests; no paid GPU as a side effect.
6. `R57B_DEV_EVAL_READY`: frozen old R55 regression ONLY and separately selected nonprotected diagnostic worlds; hold out independent R56/R50 material. Multiple tests over the same exposed 20 do not turn them into fresh independent questions.
7. Only then separately request written Owner approval for paid training and bounded cost/one Job. **Never auto-execute.**

## 6. Evaluation and falsification

- Unchanged **R46 checkpoint-7** is the main comparator. R54 checkpoint-16 is a retained negative comparator, not silently promoted.
- Pre-register direct v0.3-B-versus-v0.2 blind pairwise preferences plus six scores: continuity, characterization, instruction adherence, prose, interactive progression, player agency. Track material regressions and severe hard-rule cases separately; no trading away player agency to improve prose or vice versa.
- Evaluate old exposed R55 20 only as a regression suite. Any post-training *fresh* validation requires unexposed world components, no data-selection feedback, independent reviewers and world-clustered uncertainty. R50 is sealed and has **0 formally admitted final-test cases** at current record; do not open or infer it is ready.
- Stop/hold if data provenance, independent-world isolation, exact template parity, or quality/safety gates cannot be verified. A format-PASS judgment is not a human semantic-PASS label.

## 7. This branch's immediate no-GPU deliverables

- Contract (this file).
- JSON Schema and private-record verifier with synthetic tests.
- Count-only source inventory with evidence refs and confidence limitations; no private UUIDs, candidate tokens, narratives or R50 source material.
- Owner-side dry-run checklist for locating **40–60 non-test candidates** and completing the private intake manifest. No assumed accession count.

**Explicit status:** `R57B_DESIGN_ARTIFACTS_ONLY__NO_DATA_ACCEPTED__NO_TRAINING__R50_UNTOUCHED`.
