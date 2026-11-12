---
name: storyforge-real-quality-review
description: "Run frozen StoryForge REAL1000 Chinese interactive-fiction dual-model Quality-v1 screening through shared protocol profiles, synthetic preflight, private resumable receipts, and independent evidence-based adjudication."
---

# StoryForge REAL1000 Quality Reviewer Skill

## Scope
Only for the Owner's frozen R60 REAL1000 candidate pool (6 seed + 994 expansion).
Use on branch `r60/common2-cpu2-owner`, without editing another Agent's worktree.
Do not mutate the source pool or existing Gold/locked regression sets.
No GPU, SFT or training admission. The Common2 wrapped-System HF CPU 2/2 pass
is **technical input evidence**, not a quality review of the 1000 candidates.

## Source-of-truth and architecture
- Review standard: `docs/standards/GOLD_QUALITY_PIPELINE_CN.md`.
- Execution: `docs/R60_REAL1000_PILOT5_START_20261112_CN.md` (latest §8).
- Scoring/rubric and request validation: `experiments/r58_quality/r60_real_ai_dual_review.py`.
- Provider-specific HTTP request construction: `experiments/r58_quality/r60_reviewer_transport.py`.
- Frozen source, batch checkpoint, case SHA, safe aggregate, two reviewers:
  `experiments/r58_quality/r60_real_quality_batch.py`.
- Synthetic-only service compatibility: `experiments/r58_quality/r60_reviewer_protocol_probe.py`.
- Never introduce a new duplicate scoring rubric, token preflight, collator,
  JSONL writer, or generic HF job orchestrator in this Skill.
- 6 dimensions floor: `4/4/3/4/4/4`. Severe booleans
  `serious_player_agency`, `hard_fact_or_ban`, `safety_exclusion` need
  semantic evidence. Model verdict plus exact quote existence is not truth.

## Order of operations
1. Owner Mac read-only expansion inspect must return
   `EXPANSION_TARGET_REACHED__NOT_ADMITTED`, total=1000.
2. Confirm both distinct **actual** model IDs and their real OpenAI-compatible
   base URLs. Candidate A: Claude Opus 5.5 via 4Router,
   `claude-proxy-top-system`. Candidate B: official DeepSeek Flash,
   `deepseek-chat`. Historical IDs may change; never invent models/endpoints.
3. From Owner Mac run both offline synthetic protocol probes, then
   `--execute` for precisely one synthetic request to each actual service
   (SAFE `REVIEWER_SYNTHETIC_API_PASS__NO_PRIVATE` for both).
   The proxy may reject `messages[0].role=system`; its profile puts the
   instruction in top-level `system` without forced json_object or temperature.
   DeepSeek uses ordinary system messages; do not apply Qwen Thinking sampler.
4. Set `R60_CLAUDE_KEY`/`R60_DEEPSEEK_KEY` in private shell env.
   Owner approved remote private-data egress for this quality workflow;
   pass explicit `--allow-remote-review`; never log API keys, raw outputs,
   original source text, local private paths or IDs.
5. `r60_real_quality_batch.py init` once to a nonexistent private directory,
   with `--protocol-a claude-proxy-top-system` and
   `--protocol-b deepseek-chat`. Do not use `--json-mode` with Claude proxy.
   Do not set `--owner-attest-independent-ai` unless Owner has checked
   reviewer independence. Never overwrite/reset/modify frozen config.
6. Run exactly one `advance --max-cases 5`, then `inspect` SAFE.
   A/B must evaluate identical target and visible prior 3 messages.
   For prior outputs, resume using the same config instead of rerunning init.
7. Only after checking paired 5-case Reviewer completeness, severe semantic
   false-positive/negative risks and context HOLDs, consider a new
   Owner-authorized 25-case step. No unattended 1000-case loop.
8. `quality_v1_admitted=0`, `train_admitted=0` regardless of AI dual PASS.
   R50 exclusion/world isolation/actual historical System/roleplay
   template compatibility/training dataset freeze remain separate gates.

## Known history and limits
DeepSeek official flash 16/20 valid; Qwen BaiLian qwen3.7-flash 18/20;
14/20 strict paired in QD20. Joint PASS candidates disagree with
Claude+Codex; 3 disputed cases had independent PASS0/HOLD2/REJECT1.
Do not confuse qwen3.7-flash with historical HF Qwen3-32B.
The generic dual-review schema stores Chinese `reason_cn` but does not
yet require verbatim source quotes or Rubric v2.1 three-state per-dimension
entailment: all AI PASS labels are candidates, not adjudicated Gold.

## Regression and SAFE receipts
```bash
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
"$PY" -m pytest -q \
  experiments/r58_quality/test_r60_real_ai_dual_review.py \
  experiments/r58_quality/test_r60_real_quality_batch.py
ruff check \
  experiments/r58_quality/r60_reviewer_transport.py \
  experiments/r58_quality/r60_reviewer_protocol_probe.py \
  experiments/r58_quality/r60_real_ai_dual_review.py \
  experiments/r58_quality/r60_real_quality_batch.py \
  experiments/r58_quality/test_r60_real_ai_dual_review.py \
  experiments/r58_quality/test_r60_real_quality_batch.py
```

A real HF Job receipt or model HTTP success is not sufficient; verify the
actual applicable frozen source and evidence. Skill text is guidance, not an
execution trigger. Never auto-send private data, start GPU, or train.

## HTTP-safe diagnostics (2026-11-12)
Both synthetic probe and real private batch share public, allowlisted
`MODEL_HTTP_<code>_HOLD` for 400, 401, 403, 404, 408, 413, 429,
500, 502, 503 and 504. Other network failures are
`MODEL_TRANSPORT_HOLD`. Never print raw 4Router/DeepSeek error responses,
endpoint URLs, headers, tokens, or private prompts. 400 indicates
request incompatibility, 429 rate-limit; neither is evidence that an
interactive-fiction response is low quality. Diagnose this before
resuming the same frozen checkpoint directory.

If both reviewers report transport/HTTP errors, the batch now fails
`BOTH_REVIEW_MODELS_UNAVAILABLE` **before writing** an irreversible
case receipt. After fixing the provider, rerun `advance` using the
same frozen config. A single-reviewer failure persists one partial HOLD
receipt; never overwrite it, auto-retry in place, or invent the missing
review.

## Owner key naming / historical DeepSeek provenance (2026-11-12)
The REAL1000 new paired batch uses `R60_CLAUDE_KEY` for A and
`R60_DEEPSEEK_KEY` for B. The synthetic probe defaults by profile.
Historical QD20 is separate: `r60_real1000_qwen_deepseek20_live.py`
used `https://api.deepseek.com`, `deepseek-flash`, `DEEPSEEK_API_KEY`,
`temperature=0`, `thinking={"type":"disabled"}`. Keep that runner unchanged.
`R60_DEEPSEEK_URL` and `R60_DEEPSEEK_MODEL` may be set to these
historical exact values, but verify current access with synthetic API first.
Never echo secret environment values in CLI logs.

## Claude SAFE JSON diagnostic after DeepSeek synthetic PASS
If the Claude 4Router synthetic request returns `MODEL_JSON_INVALID`,
do not start REAL1000 `init/advance`, and **do not rerun DeepSeek** if it
already returned `REVIEWER_SYNTHETIC_API_PASS__NO_PRIVATE`.
The shared real reviewer `model_request` now accepts opt-in
`diagnose_json=True` from the synthetic-only protocol probe: fixed
codes are `MODEL_ENVELOPE_JSON_INVALID`,
`MODEL_CONTENT_MISSING_OR_NONSTRING`,
`MODEL_CONTENT_JSON_INVALID`, and
`MODEL_REVIEW_SCHEMA_INVALID`. Never show raw responses, private
input, requests or tokens. Real batch default retains strict generic
`MODEL_JSON_INVALID`. After Mac CLI update, rerun **only one Claude
synthetic probe** and inspect the SAFE code; isolate minimal transport
or response-shape fix with synthetic regression before any real private
review.
