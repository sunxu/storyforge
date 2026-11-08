# R60：10 条历史回复的 Reviewer C 独立盲语义复核（无新增 GPU）

日期：2026-11-08。状态：**代码与合成测试 PASS；Owner 私有盲包尚未实际创建，Reviewer C 尚未执行，训练不授权。**

## 前置证据及为何必须校准

Owner 通过 `storyforge_r60_hf_pilot10_owner_pairwise_safe_v1` 核验原始 Stage 全部 1,000 条 A/B 双槽对应、10/10 Checkpoint `receipt_sha256` 与 `input_sha256`；`matched_cases=0`、`unique_source_cases_in_pilot=10`，A/B 各 `REJECT=5`。因没有共同的已审核案例，不能宣布“A/B 5/5 一致”。三条 `serious_player_agency=true` 与 `player_agency>=4` 存在明显需要复核的标记/评分冲突（A 1，B 2）。原模型结果保留且不可自动用于淘汰。

公开 [Owner SAFE 原样证据](evidence/R60_HF_PILOT10_OWNER_PAIRWISE_AUDIT_PASS_SAFE_20261108.json)。来源的 raw `target_text`、历史消息、`case_key`、Owner crosswalk 和模型 Checkpoint 仍留在私有目录。

## 已完成的程序

- `src/storyforge_gold_quality/hf_pilot_semantic_c.py` 中的 `prepare`：先**重新执行**原 1,000 Stage / Owner crosswalk / A v2 / B v3 的全部源码和 checkpoint receipt 校验；仅在全部 PASS 后，生成 10 条独立随机 C ID、重新洗牌的 `C_BLIND_PACKETS_PRIVATE.jsonl`，仅含可见历史、目标与时序语义。**不含任何 A/B 的决定、评分、严重标记、原 blind_id、原始槽、来源序号**。单独 0600 的 `C_OWNER_MAP_PRIVATE.json` 保存校验映射，仅 Owner 可访问。
- 同时生成 `C_REVIEW_INSTRUCTIONS_PRIVATE.md`，请没有看过 A/B 评分与先前后验分层的独立第三模型/审核者，仅根据盲包判断三个严重维度 `player_agency / hard_rule / safety` 的证据状态：`SUPPORTED`、`NOT_SUPPORTED`、`INSUFFICIENT_CONTEXT`，并提供准确目标证据和说明。这里不直接让 C 给文学总分，优先解决严重缺陷误报问题。
- `reconcile`：在另一个 C 实际产生的 `C_RESULTS_PRIVATE.jsonl` 已存在时，对所有 10 个随机 ID、原冻结来源、Owner map/packet SHA 和 C 逐字引用全部 fail-closed 复核；只输出每维三态计数及 A/B 原严重标记与 C 的聚合对照，无逐案文本。
- **本程序不调用 LLM，不能也不会自行声称 Reviewer C 已真实执行或可证明其独立性**。即使 reconcile 完成，若没有额外执行证据，`reviewer_c_execution_verified=false`、`reviewer_c_independence_verified=false`、`semantic_severity_adjudication_complete=false`，Quality-v1 仍 0。

## Owner Mac 立即可执行：一条命令准备盲包

前提：本机此前运行的 `scripts/r60_hf_pilot10_owner_audit.sh` 已成功，A/B Checkpoint 各 5 条已在私有本地 `~/.local/share/storyforge/r60/private/hf-pilot10-owner-audit-20261108/A,B`。

~~~bash
set -euo pipefail
cd "$HOME/workspace/storyforge"
git fetch origin r60/gold192-history-v3-adapter
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter
bash scripts/r60_hf_pilot10_semantic_c_prepare.sh
~~~

该脚本沿用先前 Owner-only Stage 自动发现机制，必须恰好找到一个具备固定模型 pin 和 1,000 条输入的冻结 Stage；若没有或多个，`OWNER_STAGE_DISCOVERY_HOLD`，只能显式指定真实既有 `R60_HF_OWNER_STAGE_ROOT` 后再运行，不重建、不洗牌旧数据。程序生成全新 0700 私有目录 `~/.local/share/storyforge/r60/private/hf-pilot10-c-blind-20261108`，三份私有 0600 文件和一份 SAFE；如果输出目录存在即 HOLD，不覆盖。

**只将 `C_BLIND_PACKETS_PRIVATE.jsonl` 和 `C_REVIEW_INSTRUCTIONS_PRIVATE.md` 交给未见过 A/B 结论的独立 Reviewer C。绝不能交给 C 的文件**：`C_OWNER_MAP_PRIVATE.json`、A/B Checkpoint、A/B SAFE REJECT 汇总、任何后验 AI 分类结果。全部原文保留在 Owner 私有工作区，不上传 GitHub、不公开于聊天。

## Owner Mac Reviewer C 实际执行（推荐）

已经实现 `src/storyforge_gold_quality/hf_pilot_semantic_c_codex.py` 与一键脚本 `scripts/r60_hf_pilot10_semantic_c_run_codex.sh`：

- 每条私有 C 盲包用一条**全新** Codex CLI 会话，要求 `--ephemeral`、`--ignore-user-config`、`--ignore-rules`、`--sandbox read-only` 与临时空目录；不用旧会话，不读取 A/B 的 REJECT、评分、flag 或 Owner 映射，不重复审核已经成功保存了回执的条目。
- 模型按严格 JSON Schema 回复三个严重维度的 `SUPPORTED/NOT_SUPPORTED/INSUFFICIENT_CONTEXT`；本机进一步逐字核验原文引文与校准 ID。所有逐案结果与 CLI 执行回执私有 0600 写入，不向终端打印故事正文。任何失败 HOLD，禁止自动重新提交同一已完成任务。
- 10 条全部审核完毕时才写入 `C_RESULTS_PRIVATE.jsonl` 和 `C_CODEX_EXECUTION_RECEIPT_PRIVATE.json`；现有 `reconcile` 将核验每例执行 SHA、盲包/Owner 来源 SHA、C 引文和 C 结果，仅显示聚合 SAFE。
- 存在经过完整核验的本机 Codex 回执时报告 `reviewer_c_execution_verified=true` 和 `reviewer_c_input_blinding_verified=true`，但**不把本机回执冒充模型服务端身份公证**：`reviewer_c_independence_verified=false`、`quality_v1_admitted=0`。

**隐私及额度提醒**：运行默认 Codex 云端配置会把这些 10 条私人历史及目标回复发送给 Codex 模型服务，可能消耗 Codex 配额。不会自动提交 HF GPU 或上传 GitHub；C Agent 运行在只读沙箱与独立工作目录，但不能声称达到 OS 级绝对读取隔离。未授权云端传输时不要执行。使用本机 Ollama/其他完全离线模型需另外适配。

Owner Mac 在已登录 Codex CLI、盲包已准备的情况下：

~~~bash
set -euo pipefail
cd "$HOME/workspace/storyforge"
git fetch origin r60/gold192-history-v3-adapter
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter

# 明确授权仅十条 C 盲包发送给已登录的 Codex 云端模型
R60_C_ALLOW_CODEX_CLOUD=YES bash scripts/r60_hf_pilot10_semantic_c_run_codex.sh
~~~

可选 `R60_C_CODEX_MODEL=<可用模型名>` 显式选择模型；默认使用用户 CLI 配置，回执不会猜测其真实模型身份。必须能够识别全部 CLI 隔离选项，否则在发出任何原文之前安全 HOLD。若成功，第二段 SAFE 为 `C_BLIND_SEMANTIC_RECONCILED__QUALITY_HOLD`；**仅复制这段聚合 SAFE JSON 回聊天**，不要上传逐案结果和私人 C 映射。

---

## C 完成后：只读验证结果

独立 Reviewer C 必须按 Instructions 的 JSONL schema 提交 `C_RESULTS_PRIVATE.jsonl`（仅存私有工作区）。Owner 在原 Stage 和 A/B 本地 Checkpoint 均仍存在时执行：

~~~bash
set -euo pipefail
export PYTHONPATH="$HOME/workspace/storyforge/src"
cd "$HOME/workspace/storyforge"

# STAGE 使用上次 Owner 审计中已核验的真实存在的本机冻结 Stage。
STAGE="/ABSOLUTE/EXISTING/FROZEN_STAGE_ROOT"
BASE="$HOME/.local/share/storyforge/r60/private"
python3 -m storyforge_gold_quality.hf_pilot_semantic_c reconcile \
  --stage-root "$STAGE" \
  --review-a-dir "$BASE/hf-pilot10-owner-audit-20261108/A" \
  --review-b-dir "$BASE/hf-pilot10-owner-audit-20261108/B" \
  --c-dir "$BASE/hf-pilot10-c-blind-20261108" \
  --results "$BASE/hf-pilot10-c-blind-20261108/C_RESULTS_PRIVATE.jsonl" \
  --safe-output "$BASE/hf-pilot10-c-blind-20261108/C_CALIBRATION_SAFE.json"
~~~

注意 Reviewer C 正式模型身份和执行日志必须通过**另一个独立证据路径**确认；本地自填结果不能自动证明真实独立性。

## 审核标准与后续训练

对于玩家自主权，只看模型是否擅自替玩家说话/决定/行动；NPC 语气强势、推动剧情或主导 NPC 自身动作不能直接当作 player-agency 违规。对于硬规则，只有可见材料明确给出限制、目标明确违背才为 SUPPORTED；没有世界卡则对世界卡问题不能猜测。安全/年龄/强迫单独审查，无法判定即 HOLD。严格引文存在不等于语义支撑。

C 的复核先用于**调整评审标准和标记复核优先级**，不自动批准原始样本 PASS，也不直接放行 SFT。等独立 C 的执行证据与结果核验后，应建立小规模校准集，再决定怎样低成本批量筛选冻结 1,000 条；不再为同一个已经解决的 vLLM/Tokenizer 环境问题重复付费。
