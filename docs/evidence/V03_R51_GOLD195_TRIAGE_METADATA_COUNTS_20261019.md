# R51 Gold195 — metadata-based private triage (2026-10-19)

Source pinned to PR #2 HEAD `cfb9f4d0530eb5af3895f4fab2a81766b4e814d3` before this implementation commit. This is **real frozen source metadata inspection**, not full transcript replay, training admission, or per-row human review.

## Observed cross-tabs (195 original selected rows)

| Mutually exclusive flag set | Count |
|---|---:|
| Explicit card/timepoint evidence UNVERIFIED only | 161 |
| Card UNVERIFIED + age UNSPECIFIED | 10 |
| Source index fields absent only | 22 |
| None of these three explicit flags | 2 |
| **Total** | **195** |

171 card markers, 22 source-index metadata gaps and 10 unspecified ages. The 10 unspecified ages are all in story rank 04 and overlap the card-marker group; no source-index gap overlaps those 171 markers. **193/195** have at least one of the three explicit flags, but the other two are **not** certified. These are metadata-level patterns, not proof of historical card necessity or consent/rights clearance.

Important: 22 records lack the *two examined direct index fields*, not necessarily all transcript identifiers. Some rows have source turn/archive metadata, which may permit authenticated reconciliation later. Preserve source format differences; do not backfill the Gold originals.

## One private, actionable workpaper

Local-only command on the authorized Git checkout:

```bash
install -d -m 700 ~/.local/share/storyforge/r51
python3 scripts/v03_r51_gold195_private_triage.py \\
  --repo . \\
  --output ~/.local/share/storyforge/r51/R51_GOLD195_PRIVATE_TRIAGE_v1.jsonl
```

The command verifies frozen cohort SHA and selection index using the existing readiness implementation. It creates **195 private, versioned candidate rows** with candidate and source identities, original target digest, history-message fingerprints, explicit metadata-risk flags, evidence placeholders and two-reviewer fields; write mode is 0600 with exclusive creation. The parent directory must be private (0700); a Git-tree output is rejected. Original chat, target prose, raw reviewer reasons and identifiers do **not** go into the count-only stdout or any new tracked file.

Each row starts at `PENDING_NOT_APPROVED`, `split=null`, with `CONTENT_OR_RIGHTS_HOLD`; the 22 direct-index gaps also receive `SOURCE_POINTER_RECONCILIATION_HOLD`. Card/timepoint uncertainty remains a distinct evidence flag. **The script deliberately does not infer `CONTEXT_ONLY_POSSIBLE__HOLD` or `CARD_OR_LONG_RANGE_SOURCE_REQUIRED__HOLD` from metadata alone**: the route stays `UNDECIDED__SOURCE_ANCHORED_REVIEW_REQUIRED` until a reviewer verifies actual context sufficiency and historically available facts.

## Next review operation, not a new audit-loop

For each candidate, use authenticated original source chat with target-point cutoff to resolve pointers and contiguous history, determine local context-only sufficiency versus historical card/long-range dependency, then check age/consent/rights/forbidden rules and player autonomy. Record evidence references and two independent source reviewers in the private workpaper. Final component-disjoint Train/Val assignment requires verified linkage across stories, frozen older tests and R50, and separate engineering loss-mask checks.

R45 18 HOLD unchanged; W17 frozen; R50 test text untouched; no HF/GPU, model promotion, final seal or PR merge. The metadata screening output is not a new R51 content or training PASS.


## Owner declaration received on 2026-10-19 — age, consent, content limits

The project owner stated in the R51 continuation conversation that they
have confirmed **age, consent and content-boundary compliance** for the
candidate material. Record this as **OWNER_ATTESTED__2026-10-19** for the
Gold195 admission work, not as an independently source-replayed per-row fact,
legal opinion, training-data license grant or a final model-input approval.

The ten original `source_character_age=UNSPECIFIED` metadata values remain
unchanged, because a later owner declaration does not retroactively add
historical source metadata. Their review follow-up becomes
`OWNER_ATTESTED__SOURCE_METADATA_UNSPECIFIED`, not an automatic safety
or source-chronology PASS. Avoid repeating a generic request for the
owner to confirm age/consent/content limits unless specific contradictory
source evidence arises.

The local private 195-row worksheet v1 has been reported successfully
created with status `R51_PRIVATE_GOLD195_HOLD_WORKPAPER_CREATED__NO_ADMISSION`.
Its existing `source_review.age_and_consent=PENDING` records are historical
pre-declaration state; preserve v1 and record the owner declaration in a
new **local-only** worksheet version. Do not change Gold originals, silently
delete source-risk flags, upload candidate IDs or raw private review notes
to Git/CI, or claim individual source-anchored reviews have occurred.

**Remaining substantive blockers:** authenticated original-source pointer
reconciliation for the 22 direct-index gaps, context-only vs long-range/card
dependency backed by actual original conversations and target-time evidence,
training-use rights/licenses beyond the owner's age/consent/content assertion,
player-agency and rule compliance, independent source review, semantic
world-component segregation from frozen older tests/R50, and eventual
CPU tokenizer/collator loss-mask verification. All 195 remain
`training_admission=PENDING_NOT_APPROVED`, `split=null`;
`CONTENT_OR_RIGHTS_HOLD` remains until its other grounds are resolved.
No GPU/HF/inference/merge/promotion/seal is authorized by this declaration.


## R51 continuation — actual cross-link for 22 pointer-gap candidates

Compared the original Gold108 rows, its double-review index, and the
prior original-source R02 card/timepoint audit CSV pinned at Git blob
47748c7bf8f0c32aa9ec737e4223a707665c0060.

All 22/22 missing-direct-index candidates cross-link to a prior audit
record with matching candidate ID, original Assistant target SHA256,
target message ID, story ID (including 3 source_story_id fallbacks),
story rank, and an original target timestamp. Distribution: 06=5,
08=4, 09=7, 10=3, 13=3. Nine export cards postdate their targets;
none of the 22 has certified as-of card content. The older Gold108
review index has 3 blank primary story_id cells; no missing ID has been
invented or backfilled.

This is cross-linkage to an existing **historical source verifier's
metadata receipt**. It is not an actual replay of the full 65 MB
LFS source archive in this run, and does not recover the direct JSON
array index or historically valid card. All 22 source-pointer HOLDs
and all 195 training admission HOLDs remain.

### Privately prepare owner-attested version 2

After `git pull --ff-only`, from the authorized Git checkout:

```bash
python3 scripts/v03_r51_gold195_private_triage.py \
  --repo . \
  --owner-attested-v2 \
  --output ~/.local/share/storyforge/r51/R51_GOLD195_PRIVATE_TRIAGE_v2.jsonl
```

Version 2 is recreated deterministically from the frozen, hash-pinned
Gold195 sources and immutable prior R02 audit CSV. It does not modify
the already created v1. It retains all 10 original age-UNSPECIFIED
metadata markers, all original source-index holds and
CONTENT_OR_RIGHTS_HOLD, while noting the project owner's declaration
on age/consent/content only; it does **not** certify training-data
licensing or substitute for source-anchored individual review.
It adds private matched R02 metadata receipts for the 22 candidates.
It exclusively creates mode-0600 output outside the repository, prints
only aggregate counts, and does not start AI/HF/GPU operations.

## R51 v3 — read-only local raw source replay (06–15)

Prerequisite: owner reports original outer ZIP SHA256 verified and 10/10
nested original raw ZIP hashes matched. The 195-row v2 worksheet is generated.
This is not a training approval.

From an authorized checkout after pulling this commit:

```bash
python3 scripts/v03_r51_gold195_source_replay.py \
  --repo . \
  --private-v2 ~/.local/share/storyforge/r51/R51_GOLD195_PRIVATE_TRIAGE_v2.jsonl \
  --output ~/.local/share/storyforge/r51/R51_GOLD195_PRIVATE_TRIAGE_v3.jsonl
```

The script hashes the pinned original LFS outer ZIP, 58 MB nested
asset bundle, ten nested original raw story ZIPs and each selected JSONL.
For each of the 108 Gold06–15 candidates it attempts an exact source
target message ID+SHA256 match and a separately reported ordered /
immediately contiguous historical SHA256 sequence. It never invents
a source JSON pointer when the archive parser cannot substantiate one.
All 87 Gold01–05 remain source-replay HOLD here.

The v3 private worksheet is exclusively created mode 0600 outside Git.
Stdout is aggregate-only; actual original messages are never printed,
committed, uploaded or passed to CI. CI runs only synthetic ZIP fixtures.
All semantic context-vs-card judgments, rights, independent review,
Train/Val splits and admission remain HOLD. No GPU/HF.

## 2026-10-19 R51 v3 replay: fail-closed parser-schema mismatch

Owner ran the private Gold108 v3 raw replay against the already independently
SHA256-validated 06–15 original LFS archive. All eight Gold-bearing stories
(108 candidates) returned `target_unique_id_and_sha=0`, ordered history=0,
contiguous history=0. **This is not evidence of 108 invalid training targets.**
The earlier R25 original private JSONL target-identity source join reported
195/195 original target IDs, bodies and created-at timestamps; R26 reported
195/195 original preceding histories contiguous in source turn order and
recovered 132 previously truncated User–Assistant prefixes. These older
findings must not be mistaken for this new parser independently passing;
they also do not authorize admission or card-version reconstruction.

R51 v3's generic recursive ID/text parser did not recognize the actual
06–15 original export shape. The v3 private file contains *unmatched*
diagnostic rows only and **must not be used as a training approval receipt**
or basis to discard Gold. The replay program is now fail-closed if *all*
108 original target IDs/hashes are unmatched, rather than emitting a false
"replay performed" success. Root cause remains pending schema diagnosis.

### One privacy-safe schema probe, no new workpaper

Run in the owner's verified checkout (with the LFS archive already pulled):

```bash
python3 scripts/v03_r51_gold195_source_replay.py \
  --repo . \
  --probe-schema
```

The diagnostic checks the already pinned 65 MB/58 MB archive hashes and
10 raw-story ZIP hashes, then prints ONLY allowlisted structural field
names, container types, story rank and counts for the first original
JSONL record of each of eight Gold-bearing story sources. It prints
**no candidate identifiers, story names, message text or values** and
does not touch v1/v2/v3 or run inference. Use this structural receipt
to implement a schema-exact adapter before the next real replay.
Do not continue repeating metadata triage or alter frozen Gold/R50.


### R51 v3 failure isolation — target ID vs target-body SHA256

Owner's safe source-schema probe of 8/8 Gold-bearing stories shows an
original root JSONL object with a `messages` array; each first sampled
message has typed `id`, `content`, `role`, `turn_index`,
`created_at`, `status`, and `metadata`. Thus the previous
generic source parser **should have been able to encounter
these messages**, and schema shape by itself does not explain 0/108
unique matches.

The existing offline R51 source-replay tool now supports a separate
aggregate-only diagnostic on all 108 candidate IDs and expected target
SHA256s. It independently counts candidate hits in *direct*
root.messages IDs, source content UTF-8 SHA256s, matching ID+SHA
pairs, unique ID+SHA pairs, and the prior recursive parser. A
source-record count helps identify repeated export snapshots.
Run with private v2 already present:

```bash
python3 scripts/v03_r51_gold195_source_replay.py \
  --repo . \
  --probe-matches \
  --private-v2 ~/.local/share/storyforge/r51/R51_GOLD195_PRIVATE_TRIAGE_v2.jsonl
```

This command never overwrites any worksheet, emits only per-story-rank
counts without original texts, IDs or hashes, and performs no
training admission. Match-level evidence is diagnostic, **not**
authorization to automatically clear the 22 pointer gaps or train.
Once counts identify the precise mismatch, correct the parser or
historical mapping and do one fresh replay into an exclusively
created *new* local v4 rather than silently reusing the failed v3.


## R51 source-replay v4 correction after 108/108 original-source ID+hash match probe

The owner-provided aggregate diagnostic found, for all eight Gold-bearing
06–15 stories, **108/108 exact unique source root.messages ID+body-SHA256
pairs** and 108/108 matches in the previous recursive parser. The first
R51 v3 had reported 0/108 not because target IDs or bodies differed, but
because the recursive traversal processed nested metadata objects and
counted multiple events under an inherited original message ID, then
required exactly one event per ID. The outer archive and 10 nested
raw-ZIP SHA256 checks remain unchanged and PASS.

The corrected local v4 replay reads only the original top-level
`messages` array, preserves the true original array index and
`turn_index` in private evidence, requires unique target ID + SHA256 +
Assistant role, checks history role+SHA ordered subsequence and immediate
preceding suffix separately, and counts consecutive original turn
indices independently. A mismatch in ANY of the 108 target identities
fails closed before creating v4. It does **not** assert that every
history window must be consecutive if the real source says otherwise.
The previous failed v3 file is retained but not used as proof.

Run in the owner's authorized checkout after pulling:

```bash
python3 scripts/v03_r51_gold195_source_replay.py \
  --repo . \
  --private-v2 ~/.local/share/storyforge/r51/R51_GOLD195_PRIVATE_TRIAGE_v2.jsonl \
  --output ~/.local/share/storyforge/r51/R51_GOLD195_PRIVATE_TRIAGE_v4.jsonl
```

The source-specific pointer-location check for 22 candidates can
now be independently evidenced if exact root ID/SHA succeeds, but
their previous HOLD flags are **not** automatically removed.
All story/world/card-context decisions, content rights, reviewer
signoff and train/validation admission stay HOLD.
No original chat text, character name, candidate ID, original message
ID or per-record hash enters Git or terminal output.
