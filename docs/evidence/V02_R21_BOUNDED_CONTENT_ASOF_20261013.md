# StoryForge v0.2 — R21 bounded content and as-of audit (2026-10-13)

**Formal training admission:** `PENDING_NOT_APPROVED`. **Frozen Gold modified:** no. **Training launched:** no.

## Delivered

- Reviewed the current User input, target Assistant response, and adjacent prior history for **40/40** of the R18 first-lane diagnostic samples. Each review has an individual human-authored observation and a source-bound excerpt, not a keyword-only classifier. This is **bounded local-context review**, not fully independent end-to-end canon or policy clearance.
- **20/40** records were flagged for additional attention (examples: campus age context, player autonomy, clinical relationship, vulnerability, consent, prior timeline facts, family-and-child context). The other 20 were not flagged under those local criteria; **neither group is content approved**.
- Inspected export-time story-card evidence for **13/13** v0.2 stories, 10 of which have R18 diagnostics. **Zero** cards were mapped to a proven target-turn effective version; the frozen R07 preview does not carry the relevant target event timestamps. Ages seen only in later exports are not backdated.
- Preserved R20's confirmed **21** frozen candidates sharing the same story UUID as a v0.1 Train story. **Zero** of the first 40 have that exact UUID overlap, but linked-world independence is still unknown.
- Reused the real R18 HF Job `6acdeae181fefd5110e1963c` result of 40/40 reported internal tokenizer/mask consistency **without rerunning the model**. R18 is not yet a definitive test of any future final-context derived dataset.

## Reproducible provenance

- Parent R20 archive SHA256: `a9cccce1d9324b248efebaa70e1b1758059e6c22a949de3f12d66a16df174d9a`
- Frozen R07 uniform preview SHA256: `21255ffaf3460721bfbd89fb448e4cf5bcf53e98d3eec76585a7817e8bafd210`
- Supplementary card evidence ZIP SHA256: `c7bfd1bc3d3366f80b21bb3709fad3f6367b62ae12418010dc9e3a1e9e5b060b`
- Private R21 full ZIP SHA256: `b369fcf58678a38d922c00e4fbf20e59956ac7b8a035a1b41d054e789b7cbfa4`
- Portable independent unzip verifier: `R21_EVIDENCE_CONSISTENCY_PASS_ONLY`; intentional source-hash tampering was rejected. This does not establish full human safety or canonical approval.

## Remaining blockers

- **40/40** first-lane content/age global signoffs remain open; **0** formally content-approved.
- **0** exact effective-date story-card bindings have been proven.
- v0.1 cross-story, same-character, aliases and world group link graph remains incomplete; UUID-only isolation is not sufficient.
- **0** genuinely new, untouched held-out stories are reserved; v0.1's original held-out test cannot be relabeled as unseen v0.2 test.
- **0** v0.2 approved Train/Validation/Test assignments; **25/40** diagnostic original records lack `split_group`.
- The 38 existing HOLD, 99 opening truncation, and 18 special age/content-lane candidates remain blocked. The 195 source Gold responses have not been changed.

The private original dialogue and R21 per-sample witness JSONL remain in the conversation-provided ZIP; **do not commit those to GitHub**. No training job is authorized. Next action: obtain source turn timestamps and effective card versions, approved cross-world mappings, final review of the 40 with full canonical context, and reserve a fresh held-out set before creating a split.
