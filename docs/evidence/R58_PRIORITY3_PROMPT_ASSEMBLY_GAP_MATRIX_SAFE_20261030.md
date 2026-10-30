# StoryForge R58 — Priority3 历史 Prompt 拼装与来源证据缺口审计（SAFE）

**日期：**2026-10-30  
**源码参照：**[`sunxu/RolePlay@e9fe29c42434caeb0bac5acc91845ab4741ecb2b`](https://github.com/sunxu/RolePlay/tree/e9fe29c42434caeb0bac5acc91845ab4741ecb2b)（**不是**已证明的历史生产部署 SHA）  
**证据：**源码调用路径核查 + Owner SAFE 回执；未读取、复制、上传私有故事正文、目标消息 ID、用户 ID、请求 ID、哈希或密钥。详细逐项清单位于 [对应 JSON](R58_PRIORITY3_PROMPT_ASSEMBLY_GAP_MATRIX_SAFE_20261030.json)。

## 一、实际完成的工作

基于固定源码梳理出 **18 项与真实送模 Prompt / 原始请求来源相关的检查项**，其中 **16 项阻塞 byte-exact**，另有 2 项只能说明在这一**固定源码版本**中禁用、并不能证明历史线上也禁用。矩阵严格区分：

- `SOURCE_CODE_VERIFIED_RUNTIME_UNKNOWN`：在固定源码中核实如何执行，**不能自动推断目标历史请求执行了这一分支或得到相同文本**。
- `OWNER_REPORT_VERIFIED_SOURCE_ONLY`：三条私有来源、12 项指纹、33 条历史消息的 Owner 本地证据通过；不等同请求当时实际加载的所有数据。
- `OWNER_REPORT_CONDITIONAL_3_OF_3`：3 组各 11 消息的**条件性**历史窗口；请求时会话摘要游标没有直接证明。
- `MISSING_DIRECT_LINK`：当前请求关联最后仍有 **AUTHOR 2 / CURRENT_PUBLIC 4 / OLD_PUBLIC 2** 候选，无法锁定实际 API request_id。
- `MISSING_RUNTIME_EVIDENCE`：原始 provider request、历史部署 commit 或运行参数没有来源证据。

当前 Train / Validation / Teacher **全部仍为 0**；所有请求相关结论一律 `HOLD`。

## 二、Prompt 组成结构（来自源码，非历史字节复原）

固定源码的典型文字聊天路径：

```text
storyRow.v2_data（按 Author/Reader 权限取）
  → localizeStoryForReader(outputLocale)，openingIndex 可能选不同开场
  → applyPersonaMask（按会话/用户激活的人设，失败可回退默认）
  → buildV2RuntimePromptParts(draft, baseMode)
        base + components + hard-constraint tail
        + buildV2OutputLanguageSystemConstraint(outputLocale)
  → buildMemoryContext(...)
        rolling_outline / recent_summary / legacy memory_summary
        + stage、director、retrieval facts、entity/volume memories
        + last status/phone/ambient/components 等
        （并行、有预算、超时与缺省回退）
  → companion instructions / player identity / anti-repeat
        + meta-command、retry-warning、eventDirective
  → DB completed history → regeneration/continue/resume 特殊分支
        → selectSummaryHistoryWindow / align to first user
        → structured/policy/degenerate/repeated-assistant scrub
  → messages = [system, ...llmHistory]
  → optional inline suggestions contract appended to LAST user
  → locale reminder / named-speaker requirement appended to LAST user
  → generateCompletion or generateStreamingCompletion (provider/model/options)
```

上述仅是**所参照源码的一个概括性条件流程**，并非严格串行执行顺序：源码在最终 system 拼装前加载并裁剪历史、RAG/记忆也并行计算；部分分支会提前短路，失败时跳过注入。本图不用于生成自称 bit-exact 的 Prompt。

特别注意：
1. **System Prompt 并不等于冻结故事卡。** Reader 语言版本、个人面具、native/legacy Base 灰度模式及组件模板均可能变更。
2. **动态记忆并非只包含摘要。** 上轮 status/phone/ambient、阶段状态、卷记忆、实体卡、RAG 检索和超时回退都可能改变它。
3. **数据库可见的用户正文并非最后送模 User 文本。** 客户端类型和 Inline Suggestions 灰度决定是否追加格式契约；语言提醒和点名发言要求还会追加到最后 User。
4. **11 条只是条件窗口。** 生成前还可能有历史裁剪、policy/degen/repeat scrub，且 Session 实际 `last_summary_turn` 尚未复原。
5. 固定源码明确把 `cacheEnabled=false`（显式 Gemini cachedContent），V2 不追加原管理端 globalSystemPrompt；**这两点只能证明 pin 代码行为，不能跨越历史部署证据门禁**。
6. `historyMsgCount=11` 在本轮的 9 个请求候选中全部命中，不具目标请求身份区分力，禁止再靠时间邻近猜测 target→request_id。

## 三、按价值排序的下一阶段

| 优先级 | 要取得的独立证据 | 一旦缺失，允许做什么 | 不允许做什么 |
|---|---|---|---|
| P0 | 当时的线上部署 commit / Runtime 配置（包括 `V2_NATIVE_BASE_ROLLOUT`） | 标记 `DEPLOY_HOLD`，参考 pin 进行条件性研究 | 将当前源码直接认作历史已部署版本 |
| P0 | 目标 Assistant 物理消息或可证明的 turn/attempt ↔ API request_id 直接因果记录 | 固定三条私有来源，保留请求关联 HOLD | 选 8 个候选中时间最近者并称为原请求 |
| P0 | 原始 provider message list、参数与可信请求快照 | 建立明确标成估计值的 offline replay 原型（须与训练集隔离） | 宣布 provider 原始字节精确一致 |
| P1 | 请求时 session/摘要游标、动态记忆快照或检索日志 | 把单个组成层标为 `CONDITIONAL` 或 `MISSING` | 用今天的最新 DB session 值替换 as-of |
| P1 | 客户端 request flags、locale、model、inline/stream/retry | 逐字段标注可能路径，维持不确定性 | 假设普通 request / 普通用户输入一定就是当时发送的内容 |

## 四、接下来可以安全做的事

**当前最有价值的工作是对这 18 个检查项做静态代码的条件分支覆盖与证据缺口归档，停止重复运行三案例的时间筛选**。如果日后得到有时间戳、版本、完整性边界的原始运行日志，再按上述 P0 顺序进行证明。无需刷新 SQL 动态选样；固定三案例留在 Mac 私有目录。

如果仅以机器学习研究为目的，允许在独立的 `ESTIMATED_INPUT_EXPERIMENT_ONLY` 隔离区探索条件性重放，但应在任何正式 Train/Validation/Teacher 准入之前保留严格 HOLD，不能伪装成真实 provider 请求。无需 GPU、HF CPU Job、R50 保护题或 Skill 修改。

## 五、源码位置索引

- 剧本选择 / 本地化 / 开场：[`route.ts:1675-1731`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/chat/v2/route.ts#L1675-L1731)
- 人设面具：[`route.ts:2135-2154`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/chat/v2/route.ts#L2135-L2154)
- 动态记忆与并行检索：[`context-builder.ts:225-338`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/story-v2/context-builder.ts#L225-L338)
- 历史获取 / 滑窗 / 清洗：[`route.ts:2275-2453`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/chat/v2/route.ts#L2275-L2453)
- Base 灰度 / Prompt Parts：[`route.ts:2490-2533`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/chat/v2/route.ts#L2490-L2533)
- System 动态注入 / 最后 User 指令：[`route.ts:2585-2809`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/chat/v2/route.ts#L2585-L2809)
- 真实 provider 调用入口：[`route.ts:2965-3038`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/chat/v2/route.ts#L2965-L3038)

**阶段标识：** `R58_SOURCE_PINNED_PROMPT_GAP_MATRIX_COMPLETE__RUNTIME_REQUEST_AND_BYTE_EXACT_HOLD`。PR #7 Draft、Skill v0.1 原样、正式训练准入仍为 0。
