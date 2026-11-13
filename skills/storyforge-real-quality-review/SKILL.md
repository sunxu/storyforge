---
name: storyforge-real-quality-review
description: "Run frozen StoryForge REAL1000 Chinese interactive-fiction dual-model Quality-v1 screening through shared protocol profiles, synthetic preflight, private resumable receipts, and independent evidence-based adjudication."
---

# StoryForge REAL1000 Quality Reviewer Skill

> **2026-11-13 通用1000筛选方向（优先于旧Pilot5专属步骤）**：当前主目标是对完整冻结1000池建立来源→结构→独立双审→技术HOLD→语义仲裁→Gold候选→训练隔离的通用流程，不能继续仅为旧5案优化Reviewer。权威新方案 `docs/R60_REAL1000_GENERAL_SCREENING_PIPELINE_20261113_CN.md`。纯函数分流器 `src/storyforge_gold_quality/real1000_screening_policy.py` 只接受已来源绑定的证据标记，不读取私有文本或请求模型；仅输出 `QUALITY_CANDIDATE_NOT_ADMITTED` 等状态及1000全局SAFE聚合，**不能替代**现有 `hf_literary_review` / `hf_blind_stage` / 统一Quality Manifest与冻结六维Rubric。HF已完成Stage优先只读audit，不重复prepare，下一批需独立Owner授权。Gold/训练准入仍为0。

> **补充诊断（2026-11-13，Owner Mac 固定错误码聚合）**：已记录的 v2 三次请求结果为 `SUCCESS=1`、`QUALITY_FLOOR_DECISION_INCONSISTENT=1`、`SEVERE_FLAG_DECISION_INCONSISTENT=1`。已核对 `r60_real_ai_dual_review.parse_model_response`：前者精确表示 Reviewer 声明 `decision=PASS`，但至少一项六维分数低于冻结最低分；后者精确表示至少一个严重标记为 `true`，但 `decision!=REJECT`。两个失败均是**决策与分数/严重标记合同不一致**，不是已证实的传输或 JSON 语法失败。当前冻结下限为 `chinese_prose=4,character_consistency=4,npc_initiative=3,player_agency=4,rule_fidelity=4,narrative_continuity=4`，严标为 `serious_player_agency,hard_fact_or_ban,safety_exclusion`。公开 SAFE 不绑定具体失败侧、原始分数或严重标记明细，不能推断是哪一槽位、分数是多少或哪项标记为真。**不修正模型决定、不降低阈值、不覆盖任何 v2 HOLD，不重跑 Reviewer。** 后续独立语义判断需要 Owner 私有证据的单独只读路径；仅凭聚合 SAFE 无法形成逐案裁决。Pilot25、Gold准入与训练持续 HOLD。


> **最新执行结果（2026-11-13 Owner Mac SAFE，覆盖下方旧阶段说明）**：Owner 已明确授权且通过现有定向执行器完成全部3个模型请求；返回 `PILOT5_V2_REPLAY_ATTEMPTS_SAVED__NO_PROMOTION`（`model_requests=3`、`successes=1`、`attempt_holds=2`、`already_recorded_slots=0`）。随后只读 crosswalk 返回 `PILOT5_V2_CROSSWALK_INTEGRITY_PASS__QUALITY_HOLD`（`v1_cases=5`、`v1_valid_reviews=7`、`v2_recorded=3`、`v2_success=1`、`v2_attempt_holds=2`、`unresolved_slots=2`）。3份 v2 回执均已记录且不可覆盖；**只有1份新增有效审核意见，总有效意见8份**，另外2份是技术失败，不是文学REJECT或有效质量HOLD评分。SAFE 不揭示具体成功/失败侧与失败原因，不能猜测。**停止此 v2 命名空间任何自动重跑、删改或同计划重试**；后续只能做只读证据核验与已有8份意见的局部语义复核。技术失败是否另立 v3 纠错须先做私有失败原因/请求边界调查、单独版本化方案与Owner再次授权。#2/#3/#4/#5 未完成独立语义裁决，Pilot25/Gold/训练全部 HOLD；`train_admitted=0`，未写DB、未启GPU/HF Jobs。


> **Owner Mac 2026-11-13 实际 SAFE 更新**：`PILOT5_V2_REPLAY_PREFLIGHT_PASS__NO_REQUEST` 已由 Owner 回传，planned=3、recorded=0、model_requests=0。原“预检未报告”属于历史状态。直接从既存 v2 计划继续；不重做 API probe、Reviewer、v1 init/advance。新 `experiments/r58_quality/r60_pilot5_v2_crosswalk.py` 只读复用 `replay.verify` / `verify_existing_slot` 完整性校验，无请求、无Gold晋升。真实三个槽位仍需 Owner 明确批准。


> **Active handoff 2026-11-13**: Read `docs/R60_REAL1000_PILOT5_V2_AGENT_HANDOFF_20261113_CN.md` first. The 5-case real pilot HAS run; v1: HOLD3/REJECT2/PASS0, 7 valid reviewer outputs, only missing technical slots `(1,b),(3,a),(3,b)`. Owner Mac evidence integrity and the create-only v2 plan are PASS; CI synthetic replay runner Ruff+63/63 PASS; Owner Mac replay-runner preflight **not yet reported**. Do NOT rerun synthetic provider probes, `init`, `advance --max-cases 5`, or the successful 7 model reviews. The next action is offline `r60_pilot5_v2_replay_execute.py` **without execute flags**; after actual Mac SAFE and explicit Owner approval, the executor can do ONLY 3 missing-side calls with `--execute --allow-private-data-egress`. No overwrite, auto-retry, expand, GPU or train; all admission remains 0. Historical instructions below are retained for traceability.

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

### Reuse historically successful Claude transport before retrying

The proven `scripts/r60_p2b_claude_review_client_v1.py` supported:
top-level `system`, `max_tokens=12000`, OpenAI `choices[0].message.content`
as either a string or ordered text blocks, plus `finish_reason`.
REAL1000 uses these again. Complete single JSON markdown fences are
stripped only as format wrappers; **strict** six-dimension and severe-flag
validation remains unchanged. A length/max_tokens finish reason must HOLD,
never PASS. Earlier Claude `MODEL_CONTENT_JSON_INVALID` was not conclusively
explained by the 1600 cap; it was a regression risk and is fixed with tests.
If the next single synthetic Claude probe still fails, stop further trial
requests and inspect private, access-controlled metadata/raw HTTP evidence
under a dedicated debug workflow; never publish provider responses or
lower the quality threshold. DeepSeek synthetic API already PASS, no reruns.
