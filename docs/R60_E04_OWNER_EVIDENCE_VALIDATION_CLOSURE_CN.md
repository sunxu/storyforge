# R60 E04：三案依赖分组后的 Owner 证据与独立 Validation 收口

状态：`R60_THREE_SEMANTIC_PASS_ONE_LITERAL_COMPONENT__OWNER_E0_E3_HOLD__E4_NOT_READY`。

## 已完成（来自 Owner Mac SAFE；并非本次独立读取私有原件）

- 3 条实验候选语义审核均为有效 PASS；确定性审核失败 0；`context_provenance=RECONSTRUCTED_NOT_ACTUAL_SENT`。
- 3 个跨案例**完整目标在 Assistant 历史消息中匹配**的字面依赖边，形成单个包含 3 案的连通分组。不能在 Train 和 Validation 之间拆分此分组。该连通分组**不是**世界组件认证。
- 3/3 Packet 目标与当前 User 对齐；R59 工程 shape 校验通过。
- E0–E3 Owner 独立审核计数 0；历史 Train/Validation/Test 曝光及 Protected Set 完整性**未验证**；实验冻结与真实 ms-swift collator 未做；GPU 未授权。
- 冻结 28 条 A/B 候选的旧有 Owner 元数据覆盖，不是请求事实证明；已有 P6 对其余 25 条的 Request/Attempt 线索检查为零。无需再跑 P1–P6 / 扫描生产数据库。

## 立即执行顺序（不得用模板 PASS 代替证据）

### O1 — 三案 E0/E1/E2 溯源（先于寻找训练拆分）

以现有 `R60_E03_SEMANTIC_REVIEW_PRIVATE.jsonl`、`R60_E03_REVIEW_LOCATORS_PRIVATE.jsonl`、冻结 Packet 和已审核结果为精准键，只读取 Owner 已授权原件，不扩大搜索。

- **E0**：每案核对使用权/隐私，记录真实签核人、时间、不可变来源指纹与证据引用。若没有合同/授权或隐私依据，保持 HOLD。
- **E1**：确认**重建**输入的可见历史、System 版本、裁剪/清洗边界；记录缺失前缀、未知记忆/世界卡及实际发送 Payload 未证明的事实。实验路线不要求伪造真实 Provider 请求，但要逐项明示假设与风险。缺少关键可追溯信息时 HOLD。
- **E2**：逐案追查目标回复是否可作为单次 Assistant loss；核实重试、续写、拼接、UI 后处理与交付目标差别。仅“目标等于 Packet 文字”不够。缺少可复核的请求链/处理链或其它足够证据时 HOLD。
- 不可把 AI 语义 PASS 直接转化为 E0/E1/E2 PASS；Owner 可以就不充分的旧证据明确拒绝/关闭案例，保留原因。

现成能力：`r59_owner_evidence_preflight.py`（字段检查，不证明真实性），`gold_quality_review_bind.py`（Strict Binder，不应给重建实验线冒用），`quality_v1.py`（六维和世界隔离检查）。

**交付（Owner 私有）**：3 行不可覆盖的逐案 E0/E1/E2 决策记录与原件 SHA、审核者/时间、HOLD 原因；SAFE 仅统计 PASS/HOLD/REJECT 与证据缺口数量；禁止输出个人/故事/案例级身份。

### O2 — E3：同组处理并核实历史曝光

- 保留现有私有 `R60_CROSS_CASE_DEPENDENCY_PRIVATE.json`，精确字面依赖三个节点**必须在一个 split**。
- 补充世界组件归属的**独立来源**（不是当前 v2 卡片导出时刻的哈希等价）；若世界依赖涉及本组外其他候选，整个世界组件也必须统一 split。
- 使用已存在历史曝光登记/日志和 `r59_evidence_inventory.py` 的已有索引与 `quality_v1.py` 的分组约束，区分 train/validation/test 既往曝光为 true / false / unknown；unknown 保留 HOLD。禁止访问 R50 Held-out 内容。
- Protected Set 只能核对授权的**完整元数据清单**与版本指纹；“没有已发现的重叠”不是充分的无污染证明。
- 六维审核已完成，不再重复文学评分。

**交付（Owner 私有）**：三案的世界组件/历史曝光/保护集证据、逐项时间和原件 PIN；SAFE 只输出可核证比例、unknown 计数和是否满足独立 split 前提。

### O3 — Validation 世界的最小候选搜索（受证据门槛约束）

- **不要**直接把剩余 25 条冻结 A/B 候选当作“验证可用”；这 25 条已有元数据但请求线索仍是零，真实上下文/Owner Gate 未证明。
- 首选已有**独立审核且可追溯**的历史候选库存；只读取元数据、来源 PIN、世界组件、已知曝光与 Quality-v1 Owner 决策。禁止读取 R50 文本及复用 R50 做 Validation。
- 将 3 案字面依赖组作为一个原子单元，寻找**另一个经独立验证的世界组件**。同故事不同会话不能自动视为独立世界；不同故事也不能自动视为独立世界。
- 若找不到任何另一合格世界，明确结论 `INSUFFICIENT_INDEPENDENT_VALIDATION_WORLD`。不得随机拆分三个案例，不得降低 E0–E3 证据要求凑数。
- 如果 Validation 候选出现，先审查该世界的既往训练曝光和 Protected Set 交集（仅完整元数据），再规划世界隔离拆分；**不能仅凭数量达到 2 就宣布 E4 PASS**。

### O4 — 只有 O1–O3 已有实证时，推进 E4/E5

- E4：独立实验数据集 ID、全量样本 PIN、依赖组/world 统一 split、Train/Validation source manifest、不可变冻结；与 Strict Gold 和 R50 完全隔离。
- E5：复用 `r59_sft_collator_cpu.py` 的**实际** Qwen/ms-swift CPU-only 输入验证，非 schema-only；运行计算资源必须符合独立授权与费用控制。
- E6：明确 Owner 授权前 `training_authorized=false`、`gpu_started=false`。

## 不要新增重复模块

不得重写 Packet 关联、SFT shape packer、文学 Reviewer、A/B Binder、Owner 元数据扫描器、世界拆分器。若复用旧模块有真实接口缺口，提供最小兼容改动与合成测试；在此之前先从现有证据行动，而非继续“生成 HOLD 模板”。

## 验收与阶段终态

本阶段不用追求凑够训练条数；目标是给出可复核的事实决策：

1. 三案 E0–E3 每一缺口已有独立原件、签核或明确 HOLD 原因；
2. 字面依赖组不可拆分约束已传递给未来世界划分；
3. 是否存在独立 Validation 世界有可信元数据依据，不仅依据 Story ID；
4. 只输出 SAFE 汇总；数据库未写、R50 未读、GPU 未启动；
5. 如果来源证据依旧不足，结论 `E0_E3_EVIDENCE_INSUFFICIENT__E4_HOLD` 并终止重复扫描；如不存在独立世界，结论 `INSUFFICIENT_INDEPENDENT_VALIDATION_WORLD`，不宣布训练准入。

本文件是 Owner 后续核证执行计划，**不是** E0–E4 的签核或已有验证完成的声明。
