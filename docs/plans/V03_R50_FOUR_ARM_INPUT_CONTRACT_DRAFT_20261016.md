# StoryForge R50 → R56 four-arm identical-input contract (draft)

**Status: DRAFT / owner approval required / no inference / no final Held-out seal.**

The 46 retained R50 cases are content-PASS under the owner's **AI-only intake
review waiver**. The waiver does not automatically change the R56
three-reviewer *model-output* blind-evaluation plan or the promotion thresholds.
See `docs/plans/StoryForge_v03_Test_and_Training_Gates_20261014.json`.

## What is now evidence-backed

- R45 exact five-source gate: owner-reported PASS, while hidden semantic aliases
  remain a separate HOLD.
- Real CPU Qwen tokenizer (HF Job `6ad1fd155ccb47ba0f7b1ec6`): private
  46-row report independently validated by the owner's Git-native verifier;
  no overflow with 16,384 context and 1,536 reserved output; max input 8,757.
- Original 50 and derived 46 bytes are versioned separately, no original edits.
- Latest *additional* R45↔R50 2–4-character TF-IDF screening (669 original
  non-System messages versus R50 prompt/card/rule fields) found no 0.30+
  lexical candidate. **That is not a semantic-independence certificate.**

## Input contract proposed

For every one of Base/v0.1/v0.2/v0.3-A, construct the same message list and
freeze a per-case canonical message SHA before any inference:

1. System: exact private R45 generic System (SHA256 `5e1b28cd...`), followed
   by the R50 world-card and long-term-rules bracket blocks exactly as in
   `scripts/v03_r50_cpu_tokenizer_preflight_46.py`.
2. Keep all 364 historical messages unchanged, in original order, preserving
   all 12 cases with consecutive user-role turns; append exactly one new user.
3. Never pass `focus_tags`, reviewer diagnostics, reference target answers,
   per-case provenance, or a model-specific hidden instruction as prompts.
4. Use model revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`,
   frozen tokenizer/template hashes, `enable_thinking=False`, and
   no input truncation. All arm-specific runtime chat template and adapter
   identities must be confirmed **before** sealed-test inference.
5. Proposed generation contract: `do_sample=False`, nominal
   `temperature=0` (when accepted by serving runtime), seed 42,
   `max_new_tokens=1536`, and frozen stop/eos handling; log all actual runtime
   arguments. Do not quietly substitute defaults.

**The above is a proposed contract only; the owner has not approved it.**
v0.1 and v0.3-A precise adapter identities, per-arm input parity and runtime
compatibility are not all proven; they must be frozen before R56.

## Blind evaluation and release

R56 separately preregisters (a) randomized four-way best-of, and (b) truly
independent randomized v0.3-A versus v0.2 direct pairwise decisions. Four-way
winners cannot be used to infer direct pairwise win fractions. Six dimensions
remain scored independently. Report confidence at **five-world-cluster** level,
and sensitivity to shared events such as W17-009/W17-010; multiple correlated
questions or reviewer votes are not independent sample units.

Proposed release thresholds follow
`StoryForge_v03_Test_and_Training_Gates_20261014.json`:
non-tie v0.3 paired win fraction >50% with world-cluster 95% support,
six-dimension overall improvement, no decline in literary quality or
interaction progression, severe player-agency errors <=5% and <= v0.2, and
zero confirmed verbatim forbidden-line errors.
These gates still require an owner decision, and small world count may lead
to `INCONCLUSIVE_NO_PROMOTION`.

## Still HOLD

- R45↔R50 transitive world alias / paraphrase / hidden identity graph.
- Actual Base / v0.1 / v0.2 / v0.3-A runtime input equality and adapter pins.
- Owner approval of this contract (plus model-output reviewer policy).
- Final Held-out SHA256 seal, inference authorization and model promotion.

Privacy: Only this **text-free** contract and aggregate evidence belong in Git.
The 46 prompts, provenance map, per-case tokens, reference text, private blind
mapping and source story records remain outside normal Git commits.

### Historical v0.1/v0.2 adapter references (not runtime approval)

The existing v0.1 baseline checkpoint-9 registry records Adapter
`621d7328056758607c9d7797282ae4d5803cdb1727dab6b40a321ee959dd2478`
(see `docs/HF_RUN_REGISTRY.md`). The R46 v0.2 evidence records Base revision
`1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` and Adapter
`bec4ba74d858db3ff117d581478ef9cac41b1ecc7ea2a67523f6db1096addf2b`
(see `docs/evidence/V02_R46_GPU_TRAINING_ACCEPTANCE_20261014.json`).
These are **historical recorded hashes**. They do not demonstrate that any
R56 runtime has loaded the exact four arms or used identical inputs.
v0.3-A remains untrained/unselected under the current gate evidence.
