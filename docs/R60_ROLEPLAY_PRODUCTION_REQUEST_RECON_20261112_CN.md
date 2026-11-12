# StoryForge R60 — RolePlay生产生成输入历史溯源与R60两条共同PASS恢复交接

日期：2026-11-12。作用范围：**只读历史证据核对，禁止自动开启采集、修改RolePlay生产或启动GPU**。

## 1. 已实际定位生产源仓库，不再只凭StoryForge的训练Compiler推测

真实生产代码在 **`sunxu/RolePlay`**，不是`sunxu/storyforge/src/storyforge_dataset/compiler.py`。GitHub已直接读取：
- [V2生成入口 `src/app/api/chat/v2/route.ts`](https://github.com/sunxu/RolePlay/blob/main/src/app/api/chat/v2/route.ts)
- [V2 Prompt索引 `src/lib/story-v2/prompts/index.ts`](https://github.com/sunxu/RolePlay/blob/main/src/lib/story-v2/prompts/index.ts)
- [Runtime基础/组件/尾部 `src/lib/story-v2/prompts/runtime.ts`](https://github.com/sunxu/RolePlay/blob/main/src/lib/story-v2/prompts/runtime.ts)
- [System基本构造 `src/lib/story-v2/prompts/base.ts`](https://github.com/sunxu/RolePlay/blob/main/src/lib/story-v2/prompts/base.ts)
- [Runtime Base会话灰度 `src/lib/story-v2/prompts/runtime-rollout.ts`](https://github.com/sunxu/RolePlay/blob/main/src/lib/story-v2/prompts/runtime-rollout.ts)
- [生产部署记录 `.claude/docs/v2-production-release-20261110.md`](https://github.com/sunxu/RolePlay/blob/main/.claude/docs/v2-production-release-20261110.md)
- [既有生成原文留证方案 `.claude/plans/2026-11-07-v2-generation-evidence.md`](https://github.com/sunxu/RolePlay/blob/main/.claude/plans/2026-11-07-v2-generation-evidence.md)
- [证据Worker实施状态 `ops/evidence/README.md`](https://github.com/sunxu/RolePlay/blob/main/ops/evidence/README.md)

### 当前源码能够证明的调用构造关系（**不能直接外推到每一条历史请求**）

1. 用户请求并不是直接取`user_stories.initial_system_prompt`。当前V2调用从`user_stories.v2_data`取得草稿，可能做阅读者语言本地化、开场选择、persona mask覆盖；服务端`buildV2RuntimePromptParts(v2Draft, {baseMode})`构造`base+components+tail`，再加语言约束、摘要/结构化记忆、用户伴侣指令、玩家身份约束、重试/反复/事件动态指令等，作为真实`messages`里的System。当前数据库这两个目标对应旧字段`initial_system_prompt`和`world_setting`为空，不代表它们生成时没有System/卡片。
2. 当前正常V2历史由`V2MessageService.getRecentMessages(sessionId, effectivePruneMaxKeep*2, userId)`取同一Session已完成的消息，再用`pruneHistoryBySummary`限制窗口；**当前代码默认`PRUNE_MAX_KEEP_MESSAGES=12`**，但存在superadmin评测覆盖、更早版本的不同默认值，以及从`legacy_uncardd`到正常摘要滑窗的不同分支。生产LLM消息还可能经过结构化残留清理、拒绝页过滤、退化/复读占位处理、当前User追加语言提醒等。空输出降密重试可仅保留**6条历史**。103/243条持久化历史本身并非实际发送的消息窗口。
3. 当前代码记录`ChatLatencyMetricsService.record`及`tokenBreakdownForMetrics`，包含历史消息数、prompt版本/灰度选择、system/history token估算、request_id及model等结构性线索；并不保存完整送模正文。指标有保留期限，不可用“查不到”证明当时未运行。
4. 有可变`Runtime Base`灰度（`V2_NATIVE_BASE_ROLLOUT_PCT`及`_MODELS`）和Provider模型映射/内部重试。即使固定一个Git提交，没有**当时环境值、实际story`v2_data`版本和request证据**，仍不能声称精确复原历史Prompt。

### 生产证据留证项目已存在，但不能倒填R60历史

`sunxu/RolePlay`曾在2026-11-07至11-11实现 **V2实际生成输入留证与受控证据导出**（独立工作包A）。它覆盖原始发送body、物理Provider attempt、缓存/重试、输出处理和原消息提交关系；相比Stage R26/R27推断Prompt更接近真实证据。

真实部署记录确认：**2026-11-10 10:51:13 UTC+8**切换代码`118090a637356686701fd4a2825f3d75f30c031f`，V2新生成于**10:52:02.950 UTC+8**恢复；**留证采集、Worker、导出依旧关闭，未签发grant**。2026-11-11的独立Provider见证器仅是合成联验，不接入日常聊天。不能认为之前的历史请求已被自动补存。

2026-11-12本阶段另使用已连接的只读Supabase核实结构（不读私有两条的正文/ID）：`public.user_stories.v2_data`真实存在，目前约5346条故事有非空值。留证相关`v2_generation_evidence`、`v2_generation_evidence_exports`、`v2_generation_evidence_grants`、`v2_generation_evidence_request_links`当前计数**均为0**。这与项目留证关闭记录一致，但**只说明此时这些表无记录，不构成未来或外部日志一概不存在的证明**。

## 2. R60真实Owner证据

已完成双共同PASS独立文学审查2/2，通过Supabase只读恢复103条/243条（共346条）在目标之前的**已持久化完成消息**；与最初冻结三消息的ID/原文2/2精确匹配。Owner SAFE`QD20_COMMON2_PERSISTED_HISTORY_RECOVERED__TRAIN_CONTEXT_HOLD`，`actual_sent_system_verified_count=0`、`historical_world_components_verified_count=0`、`r50_complete_exclusion_verified=false`、`train_admitted=0`。文件保存在Owner Mac私有`r60-real1000-qd20-common2-supabase-recovery-v1`中，不应提交原文/ID到普通Git或聊天。

## 3. 优先查明目标生成时间，再锁定对应RolePlay实现

新增只读CPU工具`experiments/r58_quality/r60_roleplay_request_era_cpu.py`及`tests/test_r60_roleplay_request_era_cpu.py`。严格使用已经保存的Owner私有恢复文件里的真实target`created_at`，输出**仅两个数量桶**（2026-11-10 10:52:02.950 UTC+8生产切换之前/之后），不输出精确日期、故事/会话/消息ID、正文、连接串，不访问DB。此工具**不是**历史部署SHA证明；即使目标在切换之后，也不能仅据时间断言一定运行此版本（还需要PM2/部署实例关联及运行时环境）。

Owner Mac仅需CPU：
```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
python3 -m pytest -q tests/test_r60_roleplay_request_era_cpu.py
BASE="$HOME/.local/share/storyforge/r60/private"
python3 experiments/r58_quality/r60_roleplay_request_era_cpu.py \
  --recovery-dir "$BASE/r60-real1000-qd20-common2-supabase-recovery-v1"
```
预期`ROLEPLAY_TARGET_ERA_CLASSIFIED__HISTORICAL_REQUEST_UNVERIFIED`。获得两个时间桶后：
- 切换前：必须寻找目标时段`RolePlay`真实部署SHA和`route.ts`、`prompts/*`、记忆模块的历史版本（不能套用2026-11当前的12消息默认）。
- 切换后：至少优先对照固定已知`118090a6`部署点，但仍需针对每条target创建时实际运行的后续部署和动态开关。
- 只读检索Owner已授权的同target/session时代`chat_latency_metrics`结构字段、`stream_generation_id`、旧日志和request上下游关联，**先只汇总可用记录与证据类别，不读/输出原文**；若超30天保留期限已清理，应标记`EVIDENCE_NOT_RETAINED`而不是`NO_PROMPT_SENT`。
- 再审查当时对应`user_stories.v2_data`版本/是否存在immutable revision和原生成时`memoryInjection`快照。缺失则不伪造。可另行定义`SOURCE_BOUND_DERIVED_TRAINING_INPUT`方案，清楚区别于`HISTORICAL_WIRE_REQUEST_VERIFIED`。

## 4. 准入门禁

这是**生产逻辑证据调查**，不修改RolePlay仓库或线上服务，不开启留证抓取、导出或任何SQL迁移，不拿新的用户消息做实验请求。训练数据的文学质量、完整R50评测隔离、训练System实验方案、Qwen CPU Tokenizer/Collator仍是分别独立的门禁。两条共同PASS不是正式Gold或SFT准入。任何产物只输出聚合SAFE，原私有输入与历史审稿文件完全不变。

**当前状态：`ROLEPLAY_PRODUCTION_IMPLEMENTATION_LOCATED__R60_ORIGINAL_WIRE_INPUT_NOT_VERIFIED__NO_TRAINING`。**
