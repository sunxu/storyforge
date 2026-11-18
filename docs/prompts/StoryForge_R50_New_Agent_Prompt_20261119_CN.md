# 新 Agent 接手提示词：StoryForge R50 46-case Protected Held-out 剩余审计

你现在接手 GitHub 仓库 `sunxu/storyforge` 的 R50 46-case Protected Held-out 剩余审计与证据闭环工作。

## 最高优先级：先读交接材料，禁止重复劳动## 文档所在分支与证据 ref

本提示词、当前任务书和交接包目前位于 Draft PR #33 分支 `docs/r50-agent-handoff-20261119`，尚未合并 main。2026-11-19 审计证据位于独立 Draft PR #32 分支 `docs/r50-world-cpu46-audit-20261119`。读取时必须显式指定正确 ref；不要因 main 暂时找不到这些新文件而认定它们不存在，也不要假定 PR 已合并。



先完整阅读：

1. `docs/r50/R50_46_PRESEAL_TASKBOOK_20261119_CN.md` —— 当前任务书、证据优先级、剩余任务和 no-repeat ledger。
2. `docs/handoffs/StoryForge_R50_Agent_Handoff_20261119_CN.md` —— 当前仓库/PR 状态、交接范围和第一轮汇报要求。
3. `docs/evidence/V03_R50_WORLD_CPU46_ROLE12_AUDIT_20261119_CN.md` —— 2026-11-19 审计结论（目前位于 Draft PR #32 分支，先确认 PR 状态，不要假定已合并）。
4. `docs/evidence/V03_R50_ROLE12_OWNER_INTAKE_SAFE_20261023.md`。
5. `docs/evidence/V03_R50_CPU46_OWNER_TOKEN_LENGTH_SAFE_AGGREGATE_20261023.md`。
6. `docs/evidence/V03_R50_W17_AI_SEMANTIC_DECISION_SAFE_SUMMARY_20261019.json`、`V03_R50_W17_FULL_MESSAGE_AI_REVIEW_OWNER_RECEIPT_20261019.json`、`V03_R50_W17_TIMEPOINT_METADATA_OWNER_RECEIPT_20261019.json`，均在历史分支 `audit/r49-r50-source-intake-20261015`。
7. `docs/evidence/V03_R50_OWNER_STORY_INDEPENDENCE_ATTESTATION_AND_R56_NEXT_GATE_20261023.md`。
8. 历史任务快照 `docs/r56/R56_R50_46_PROTECTED_GATE_NEXT_STEPS_20261022.md`。注意：其旧建议必须与 2026-11-19 最新 inventory 对照，不得照抄执行。

不要只读任务书摘要；必须核对 GitHub 当前 HEAD、PR #32、引用文件是否存在及其所在 ref。

## 一、当前事实（不得自行升级门禁）

### WORLD
2026-11-19 Owner read-only 输出：
- `FULL_SOURCE_BYTES_CHECKED__SCOPED_LEXICAL_SCREEN__SEMANTIC_HOLD`
- source pair rows=50；old full-source messages=37,165；R50 full-source messages=11,627。
- Old06_15 CRC=PASS；Old14 CRC=PASS。
- same Story ID pair count=0；extra archive Source-ID conflicts with R50=0。
- exact long-message flagged pair rows=3；sampled 120-character flagged pair rows=3。
- timepoint card-field review=PENDING。
- hidden alias/world-component closure=HOLD。
- final Held-out seal=NOT_PERFORMED。

三条 flagged pair 正是历史 W17 已审查的同一对照集合（old ranks 2/4/10 对 R50 rank 17）。2026-10-19 的既有 pair decisions 全部是 `INSUFFICIENT_EVIDENCE`。同一批证据不得重新交给 AI 再审一次，并把重复结果称作新证据。

另有七个 W17 full-message gaps 已审查，七个全部 `INSUFFICIENT_CONTEXT`；344 个 dossier message entries、75 个 scoped citations；historical card timings 均未检查。W17 的 exact inference card snapshot 未验证，04→07 旧组件及其到 W17 的可能传递连接未闭合。

### CPU46
- 46/46 Token lengths verified；46/46 在 Draft input budget 14,848 内，超限 0。
- Draft context=16,384，Draft output reserve=1,536。
- Token aggregate 的 template/role semantics verified=false。
- CPU receipt 的 `full_46_token_length_and_role_checks_independently_verified=false`。
- Official Held-out admitted=0；Final Seal=false；没有 GPU、inference、training。

不要再次提交相同冻结输入的 HF/CPU Tokenizer Job。

### ROLE12
- 历史消息=364；46/46 原角色与顺序保留（Owner 报告）。
- 12 条 trailing User；12/12 连续 User append；12/12 有真实 tokenizer encoded record（Owner 报告）。
- Owner 对连续 User 的解释政策未批准。
- 四臂真实运行时 role parity 未验证。

不要重新运行相同输入的 ROLE12 Owner-local 审计；不要合并、改写或删除连续 User 消息。

## 二、任务目标

只推进真正未完成的证据门禁：

**W1. 最新 inventory 与历史证据交叉核对**
- 核实 2026-11-19 的 50-row inventory 是否完整覆盖旧 W17 dossier、来源归档、R45 来源范围和已知传递链接。
- 识别真正新增的来源、卡片版本、规则、别名、事件或运行时 provenance。
- 输出脱敏 coverage crosswalk，标记 `NEW_EVIDENCE_PRESENT` 或 `NO_NEW_EVIDENCE`。
- 不重复 CRC、词法扫描或同一对 pair 的 AI review。

**W2. 时间点卡片与规则证据**
- 优先查找 Owner 已有的、带不可变版本/时间戳/hash 的历史 card/rule snapshots，以及实际 inference prompt assembly/runtime records。
- 证明每个相关 cutoff 时刻模型真正可见的 card fields 和 long-term rules。
- 当前卡片、导出时卡片、创建/修改时间等 metadata 不能代替 inference-time prompt proof。
- 若历史快照不存在，明确记录 `SOURCE_UNAVAILABLE` 并维持 HOLD；不要用当前内容回填历史。

**W3. Alias / event / transitive world-component closure**
- 仅在有新来源证据时重新裁决三组旧 pair。
- 纳入已记录的旧 04→07 confirmed edge 和两个 known transitive old links。
- 核实旧组件与 R50 W17 的可能传递连接。
- 区分平台模板复用与真实人物、组织、场景、事件、时间线、剧情连续性。
- 无证据的边保持 `INSUFFICIENT_EVIDENCE`，整体继续 HOLD。

**W4. ROLE12 单独门禁**
- 不重跑已完成的结构/Tokenizer 审计。
- 向 Owner 请求一个明确的连续 User 解释政策决定。
- 在该决定后，核实 Base/v0.1/v0.2/v0.3-A 的实际 role sequence、System/card/rule 顺序、tokenizer/template pin、truncation、generation reserve、EOS/sampling 等运行时一致性。
- 不允许改写冻结数据以消除角色差异。

**W5. 仅准备，不执行最终评估**
- W1–W4 通过且 Owner 批准后，才准备四臂 preregistration、评分合同、盲审独立性、世界聚类统计、GO/NO-GO 阈值和答案/随机化 custody。
- 当前不允许 final seal、inference、GPU、training 或 promotion。

## 三、明确禁止重复的工作

以下均已有结果，不得在相同数据/证据上重复：
- Old06_15、Old14 CRC 检查；
- 2026-11-19 50-row scoped source inventory / lexical screen；
- 2026-10-19 三组 W17 pair AI review；
- 2026-10-19 七个 W17 full-message gap review；
- CPU46 HF Tokenizer Job 与 46 条 Token-length aggregate；
- ROLE12 Owner-local audit；
- 再次询问 Owner 是否认为故事世界独立（2026-10-23 attestation 已记录）。

旧任务快照建议的 R45 full-history scan 也不能直接照做。先确认 2026-11-19 inventory 是否已经覆盖其 exact SHA-pinned source scope；只有明确发现未覆盖的必要范围，才提出最小增量检查，并等待 Owner 授权。

## 四、证据与隐私约束

- 不要求用户把 R50 正文、prompt、target reply、case ID、source-message ID、映射或答案贴入聊天。
- 私有数据只留在 Owner 控制的目录；任何获准检查必须 read-only。
- GitHub 只提交脱敏 aggregate SAFE receipt、证据指针和门禁状态。
- 不修改原始 50 条、46 条 PRESEAL、4 条排除项、R45 冻结源、System、历史消息或答案。
- 不接触数据库写操作，不访问答案密钥，不解盲。
- 不启动 HF Job、GPU、model inference、training，不晋升模型。
- 不修复无关的全仓 Ruff 技术债；PR #32 CI 已在 repository-wide Ruff 阶段失败（202 个既存 findings，测试阶段被跳过），本次文档任务不应扩大为全仓清理。
- 不把 Owner attestation 或 Owner-local receipt 写成 independent source verification。

## 五、交接后的第一轮输出格式

先不要改文件、运行脚本或访问私有源。先向用户提交一份核验报告，包含：

1. 当前 main HEAD、PR #32 状态、PR #32 CI 状态。
2. 上述 8 项材料中实际成功读取的文件及 ref；缺失项如实列出。
3. No-repeat matrix：每个工作项标记 `ALREADY_DONE`、`NEW_EVIDENCE_REQUIRED`、`OWNER_DECISION_REQUIRED` 或 `NOT_AUTHORIZED`。
4. W1–W4 每项具体缺少什么证据，且说明它是否已经存在于仓库/Owner receipt。
5. 任何下一步动作的权限影响和是否需要 Owner 批准。

只有完成核验后，才提出最小的下一步。不得让用户重复提供本提示词已包含的信息。不要为了“有进展”重跑已完成审计。

**最终当前状态必须保持：**
```text
WORLD_SEMANTIC_ISOLATION = HOLD
TIMEPOINT_CARD_RULE_PROVENANCE = PENDING
HIDDEN_ALIAS_WORLD_COMPONENT_CLOSURE = HOLD
CPU46_TOKEN_LENGTHS = VERIFIED_DRAFT_ONLY
ROLE12_STRUCTURE = PASS_AS_REPORTED
ROLE12_POLICY = NOT_APPROVED
FOUR_ARM_RUNTIME_ROLE_PARITY = NOT_VERIFIED
OFFICIAL_HELDOUT_ADMITTED = 0
FINAL_SEAL = NOT_PERFORMED
GPU_USED = false
MODEL_INFERENCE_RUN = false
TRAINING_RUN = false
```
