# StoryForge v0.2 — R36 focused 32-case review, provisional 85 ceiling, synthetic auxiliary eval

**2026-10-13. Formal GPU admission `PENDING_NOT_APPROVED`. No source Gold was modified, no paid GPU training was started.**

## Grounded input and exact diagnostic

The parent is R35's independently verified **89 conditional but entirely unsigned** exact-copy rows, ZIP SHA256 `7547ebada5365248a197b01a5c4a380a560cfe090b01430ae41e60740a2bd939`. Existing R27 original candidate SHA256 remains `cdecc311f05e2c700f1038f3afca09c889ff681d4ef55dc18dc7426c9d14a92a`; its genuine HF 117/117 Token/Mask PASS applies only to those unchanged original examples.

R36 reassessed the **32 R35 P1** source-flagged examples by reading their visible User turns, final supervised target and adjacent earlier Assistant excerpt, while using the inherited R31–R34 visible-window records for context. The private review JSONL stores exact user and target quotes and offsets, full message SHA256s, five optional extra historical Assistant witnesses, rationale, candidate/story IDs and **PENDING** final approvals. It is an *assistant preliminary judgment*, **not** new independent full-history human adjudication.

| Provisional category (not approved) | Count |
|---|---:|
| New source-evidenced **derivative-window HOLD recommendation** | 4 |
| Historical Assistant context contamination / scope review | 9 |
| Target detail and player action nuance review | 4 |
| Age documentation required | 7 |
| Narrative relationship/content contextual review | 6 |
| Prior status-panel formatting obligation | 1 |
| Fantasy setting/canon rule consistency | 1 |
| **Total** | **32** |

Four *new HOLD recommendations* for **short-window derivatives only**, not original curator Gold:

1. `na-gold-t0195`: target asserts a player's unexpressed previous inner tension has disappeared.
2. `s08-gold-t00183`: target claims the player repeatedly said they have poor appetite; no corresponding statement occurs in its complete R27-visible prompt.
3. `s15-gold-r02-t01460`: target asserts a noble's carriage has already arrived when the R27 visible prefix does not establish that arrival, and adds a player crown-removal action.
4. `sf12-gold-t00751`: target quotes a past comment from a named person absent from the R27 input. Earlier User merely said they chatted about unspecified amusing company events.

These are **R36 reviewer recommendations**, not project-owner approved exclusions. An authentic longer context may explain some but still requires a new versioned input and a fresh Token/Mask check. Do not silently correct/rewrite any Gold.

## Strict read-only review ceiling and hashes

Removing only the four proposed derived-window holds *for a second, more conservative review shortlist* yields **85** row-byte-identical records. Unsigned UUID-level split remains **67 Train-proposal** rows across 7 stories and **18 Validation-proposal** rows across 2 stories. **The R35 89 and all older sources are left intact.** R36 exports are named `NOT_APPROVED` / `PROPOSAL`; no `train.jsonl` for production or optimizer run.

- 85 SHA256: `6904707203c9219d398d0d38f67e782374efbf69c8448e383b1afc5fc876ba43`
- 67 SHA256: `ab7dc2e6c834d0ef138b5cbe0966a239b5883315e44aba541230fcd4bdddbb00`
- 18 SHA256: `15c897c4daa28323f5b676e08209905b629d40ec09728c086c3767531bd0eb78`

A deliberately limited named-person/world string probe checks **16 distinctive anchors** in these 85 windows and finds **0 named-anchor collisions between story UUIDs**. It does not prove independence of characters, aliases, IP, works, original full conversations or future heldout examples.

## New original but nonofficial auxiliary benchmark

A **new, assistant-authored, unscored, explicitly prohibited-from-training** evaluation draft has **20 independent prompts across two newly specified worlds**, with no reference Assistant targets:

- `潮汐档案局`: engineering/archival permissions, storm timing, player agency.
- `盐灯城的镜塔`: civic audit, double attestation, confidentiality, uncertain facts.

Private auxiliary JSONL SHA256: `15d47bd458139baf0bb2c198cd57dac03c8d2446c3fe4fa3b30781322f21432c`.

This can later support synthetic smoke/blind evaluation **if sealed and independently approved**. It is **not** the genuinely fresh independently authenticated human-backed heldout required for official training release: formal fresh heldout remains **0**, and no test results or verdicts are invented.

## Private artifact and verification

`StoryForge_v02_R36_P1_32_Target_Adjudication_20261013.zip`, SHA256 `3d7365f547a99bd9a16b15d6fd4ff0910b6e11c9aeac7657d7ac35a19daf912b` contains R35 frozen parent, all 32 hashed exact evidence records, 89-row review route, 85/67/18 immutable copy candidates, small name-overlap probe, 20 auxiliary unscored prompts, read-only verifier and SHA256 manifest. Independent unzip and `SHA256SUMS.txt` PASS. The verifier independently reconstructs 85/67/18 from exact original parent lines, verifies 32 user/target witness digests and offsets, the new 4 holds, all `NOT_APPROVED` metadata, and 20 never-scored synthetic prompts: `R36_32_EXACT_SOURCE_WITNESSES_PASS__4_NEW_HOLD_RECOMMENDATIONS__85_67_18_BYTE_IDENTICAL__TRAINING_BLOCKED`. An intentional modified-evidence test exited 2.

The archive includes private dialogue and is not added as ordinary Git data. GitHub stores **only this abstract release state and aggregate metadata**.

## Remaining final admission gates

- R36 32 P1 preliminary recommendations require independent final content/age/user agency adjudication; R35 57 other P2/P3 candidates remain as-is, not batch-approved.
- R30 25 separate origin/IP quarantines remain unchanged. No copyright/usage authorization is inferred from a name match.
- No certified connected-story, shared-world or alias-component disjoint Train/Validation graph; UUID-only difference insufficient.
- No **human-authorized independently sealed** new heldout set. Auxiliary 20 synthetic prompts do not close it.
- No signed final train/validation rows or new final compiled-input HF collator audit; no GPU expense/run authorization.

**Training release remains `PENDING_NOT_APPROVED`.**