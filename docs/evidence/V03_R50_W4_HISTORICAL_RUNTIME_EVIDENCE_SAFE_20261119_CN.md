# StoryForge R50 — W4 historical runtime evidence and parity gap (SAFE aggregate)

**Date:** 2026-11-19  
**Repository:** `sunxu/storyforge`  
**Branch:** `docs/r50-agent-handoff-20261119` (Draft PR #33; not merged)  
**Evidence type:** Owner-provided local SAFE parser outputs, existing GitHub runner/report inspection, and Owner's explicit policy approval. This is not an independent replay of private runtime logs or R50 source data.

## 1. Owner-approved ROLE12 contract

Owner explicitly approved that the 12 histories ending in User followed by the newly appended User remain two distinct consecutive User turns. All four model arms must preserve both messages independently and in original order; do not merge, rewrite, delete, or insert an Assistant message.

```text
ROLE12_POLICY = APPROVED
CONSECUTIVE_USER_SEMANTICS = TWO_INDEPENDENT_USER_TURNS
APPLY_TO = BASE, V0.1, V0.2, V0.3-A
PRESERVE_ORIGINAL_ROLE_SEQUENCE = true
MERGE_USER_MESSAGES = false
REWRITE_USER_MESSAGES = false
DELETE_USER_MESSAGES = false
```

This policy decision does not prove that any actual runtime preserved the sequence, and does not authorize model loading, inference, GPU, training, admission or final seal.

## 2. R47 historical three-arm runtime logs recovered and parsed

Owner downloaded only the two existing private `execution.log` objects and ran a local allowlisted parser. Raw logs, prompt/response text, case identifiers, adapter paths, answers and mappings were not uploaded.

| Run | Bytes | SHA256 | Lines |
|---|---:|---|---:|
| Original Base `r47-20261014T082109Z-820409` | 84,617 | `34d3e33ca1888dbc1c61cf65c0f2619ebf41bae626deea131564db8e6a927399` | 1,183 |
| Resumed run `r47-20261014T091647Z-637890` | 450,504 | `18b077671b38404ff4821c4d9fb0342b3cb9430fc5d5565c9efc1586a4c3ab7c` | 8,676 |

Arm mapping is supported by the safe log line locations plus `scripts/v02_r47_eval_runner.py` (main blob SHA `a2fa43f65b7b31631976cab1ac84b2b183b5f352`): the runner iterates Base, v0.1, v0.2 in that order, adds `--adapters` for adapter arms, and the resumed run reuses the earlier Base result. Thus original Base line 395 is Base; resumed line 395 is v0.1; resumed line 4537 is v0.2. Exact adapter paths/values were not emitted by the safe parser.

### 2.1 Matching command-level settings across R47 Base/v0.1/v0.2

- `use_hf=true`; `infer_backend=transformers`.
- `torch_dtype=bfloat16`; `quant_method=bnb`; `quant_bits=4`; `bnb_4bit_compute_dtype=bfloat16`.
- `max_new_tokens=1536`; `seed=42`; `data_seed=42`; `temperature=0`; `val_dataset_shuffle=false`.

### 2.2 Matching runtime-summary fields across R47 arms

- `template=qwen3_8`; `template_backend=swift`.
- `enable_thinking=None`; `truncation_strategy=delete`; `max_length=262144`; `max_model_len=None`.
- `top_p=None`; `top_k=None`; `repetition_penalty=None`; runtime `model_revision=None`.
- `stop` / `stop_words` are present but values were redacted; `eos_token_id` was not extracted.

Interpretation: `enable_thinking=None` is not proof that thinking is disabled. Runtime `model_revision=None` does not mean the model was unpinned: the Runner calls `snapshot_download` with its pinned `REV`, and the R47 report records `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`. Stop-value equality and effective EOS remain unverified.

R47 was retrospective inference on 20 exposed prompts / 60 responses, not training and not a fresh Held-out evaluation. It did not include the original Assistant reply as an additional arm and cannot establish R50 runtime parity.

## 3. R55 / R54-derived v0.3-A historical runtime evidence

Owner's SAFE field scan of the existing R55 runtime log (243,541 bytes; SHA256 `f83f877441c38fbb1ef705a8b2e6acd0a4603bd14fcdd280741fe9e905cdfee3`) reports Transformers/HF, BF16, BitsAndBytes 4-bit, `template=qwen3_8`, `template_backend=swift`, `enable_thinking=None`, `truncation_strategy=delete`, `max_length=262144`, `max_model_len=None`, `max_new_tokens=1536`, temperature 0, data_seed 42, validation shuffle false, and stop/stop_words present with values withheld. EOS token ID was not found.

R55 has an unresolved scope ambiguity: `seed=42` appears in invocation/runtime configuration records, while a separate GenerationConfig-like record reports `seed=None`; `top_p`, `top_k`, and `repetition_penalty` are also `None` in that separate record. Do not collapse these records into one effective configuration without an existing-record-backed precedence explanation. A `messages` marker in the log does not prove preservation of the two consecutive User roles or per-case input-ID parity.

R55 generated on 20 previously exposed development prompts using the R54 checkpoint-16 adapter. It is historical development inference, not R50 evaluation evidence. The Owner's R55 development decision retained v0.2 and marked R54 checkpoint-16 NO-GO for R50; do not infer R50 readiness from runtime similarity.

## 4. What this proves — and does not prove

| Question | Current evidence | Disposition |
|---|---|---|
| Owner's consecutive-User interpretation | Explicit approval recorded above | `APPROVED` |
| Historical R47 Base/v0.1/v0.2 command settings | Recovered logs + Runner arm order | Matching for listed fields; not R50 parity |
| Historical R55 v0.3-A-side runtime fields | Existing SAFE log scan | Partial; seed/default/stop/EOS ambiguities remain |
| Exact R50 four-arm model load/runtime receipts | None found in inspected GitHub source/evidence | `NOT_FOUND_IN_GITHUB_SEARCHED_SCOPE` |
| Exact R50 per-arm serialized role sequence / input IDs | Static Draft message-buffer hash exists; no runtime/input-ID receipt | `NOT_VERIFIED` |
| R50 case-time System/card/rule assembly | W2 search did not find authenticated cutoff snapshots or prompt-assembly receipt | `SOURCE_UNAVAILABLE_IN_SEARCHED_SOURCES` |
| R50 actual tokenizer/template and truncation behavior across all four arms | CPU46 length receipt is Draft-only; historical R47/R55 logs are other prompt sets | `NOT_VERIFIED` |
| Effective EOS and exact stop equality | Stop fields present but redacted; EOS not extracted | `NOT_RECORDED` |

The existing static Draft message-sequence SHA256 `9ad0254f740a979e9b79b458a22e61e40db4ff98fb946e0332cf172e6888565c` covers 46 cases / 364 historical messages / 12 consecutive User endings. It is not a tokenizer input-ID hash, not a runtime prompt capture, and not evidence that all four model arms received identical serialized requests.

## 5. Smallest next action — read-only Owner-local evidence inventory

Search only already-existing Owner-controlled R50 artifacts for per-arm model-load receipts, effective configuration dumps, prompt-assembly receipts, tokenizer/template hashes, and role/input-ID parity reports. Return a sanitized inventory of filenames, byte sizes, SHA256 values, run/arm counts, and allowlisted field presence/values. Keep raw artifacts, prompt contents, response contents, per-case identifiers, mappings and answers private.

If no R50-specific four-arm load/runtime records exist, record `SOURCE_UNAVAILABLE`; do not start a model, tokenizer, HF Job, GPU, inference or training to manufacture historical proof. Do not repeat CPU46 tokenization, ROLE12 structure audit, R47/R55 generation, or the completed W1/W2/W3 work.

## 6. Current gate state

```text
W1_CROSSWALK = NO_NEW_EVIDENCE__EXISTING_W17_FLAGS_RECONFIRMED
W2_TIMEPOINT_CARD_RULE_RUNTIME = SOURCE_UNAVAILABLE_IN_SEARCHED_SOURCES
W3 = NOT_TRIGGERED
WORLD_SEMANTIC_ISOLATION = HOLD
TIMEPOINT_CARD_RULE_PROVENANCE = PENDING
HIDDEN_ALIAS_WORLD_COMPONENT_CLOSURE = HOLD
CPU46_TOKEN_LENGTHS = VERIFIED_DRAFT_ONLY
ROLE12_STRUCTURE = PASS_AS_REPORTED
ROLE12_POLICY = APPROVED
FOUR_ARM_RUNTIME_ROLE_PARITY = NOT_VERIFIED
ORIGINAL_GOLD_R50_COVERAGE = NOT_ESTABLISHED_OUTSIDE_EXAMINED_SOURCES
OFFICIAL_HELDOUT_ADMITTED = 0
FINAL_SEAL = NOT_PERFORMED
R50_GPU_USED = false
R50_MODEL_INFERENCE_RUN = false
R50_TRAINING_RUN = false
```

R47/R55 historical GPU inference and R54 training are prior development activities; they do not mean this R50 audit used GPU or performed R50 inference/training.

**Privacy:** no private prompt, story, answer, source-message identifier, case identifier, mapping, raw runtime log or adapter path is included in this receipt.