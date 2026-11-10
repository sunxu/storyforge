# R60 训练证据目标纠偏：从数据库时点恢复转向实际模型输入证明

日期：2026-11-07
性质：需求与证据分类调整；不改变冻结样本、不放行训练、不变更生产数据库、无 GPU。

## 1. 决策

**StoryForge 的最终目标不是证明“数据库在目标时刻是什么”，而是证明“产生目标 Assistant 回复的那次具体模型请求实际使用了什么输入”。**

数据库 Ledger、时间顺序和 Trigger 是重要的旁证和可选恢复路线，但数据库快照本身不能证明模型收到的 System Prompt、历史裁剪、消息清洗、角色卡、世界状态、记忆注入、模型设置及重试输入。

原 R60 T1 Writer Path 扫描和 Ledger 专项工作保留为 RolePlay 数据完整性 P1，以及旧样本 C 类专项恢复的条件性依赖；**不能再作为所有 Gold192 样本进入输入证据审查的全局前置条件**。

必须区分以下三层证据：

1. **构建态：** 应用在某版本代码中构造出的模型消息及依赖；
2. **发送态：** 已序列化、实际交给传输客户端/请求适配器的消息和参数（含每一次重试）；
3. **Provider 接收/执行态：** 能取得的请求 ID、服务端回执、响应关联、模型/版本信息。若 Provider 不返回可验证的输入回显，不得把仅有本地发送留证表述成 Provider 已独立证明收到逐字节相同内容。

训练准入不能只靠 Source SHA、数据库版本或发送成功日志推定上述三层全部成立。

## 2. Gold192 现有样本证据分级（先盘点，不预判数量）

| 级别 | 严格含义 | 处理 |
|---|---|---|
| A / ACTUAL_INPUT_EVIDENCED | 有对应目标生成尝试的真实已发送模型请求，或具备等价强度、可校验的完整原始请求留证；目标输出与该尝试可唯一绑定 | 仅允许进入后续 Quality-v1 审核；不是训练准入 |
| B / INPUT_RECONSTRUCTION_VERIFIABLE | 生成时使用的完整代码版本、模板、动态变量、角色设定、世界/记忆状态、裁剪算法、序列化、Provider/路由重试选择均可固定，并有独立核查的重建一致性证据 | 待独立核查后判定；不把机械模拟默认为真实请求 |
| C / PARTIAL_INPUT_EVIDENCE | 只有消息、Ledger 或部分 Prompt/上下文、模型请求记录；仍缺失一个或多个关键实际输入要素/时序证明 | HOLD；只针对缺口进行专项恢复 |
| D / INPUT_UNVERIFIABLE | 必要输入或目标生成尝试身份/版本无法可靠建立，且没有可行独立来源 | 不进入训练；保留来源和拒绝原因 |

注意：A/B/C/D 是**输入证据层级**，和原来的 FULL_HISTORY_RECOVERED / VERIFIED_WINDOW_RECOVERED / HOLD / REJECT（数据库消息历史恢复状态）属于不同维度，不能互相替代。Reviewer A/B、11 exclusions、世界隔离、历史训练曝光、Owner 审批等原有门槛继续有效；某个 Case 获得 A 级也不能直接准入。

## 3. StoryForge P0：先做证据目录与缺口矩阵

以冻结 Gold192 的 192 个 Case 为完整集合，不按成功率设最低数量，也不改写历史内容。先不执行模型推理或训练。对每条目标样本记录以下**可验证证据状态**，敏感标识仅存在 Owner 私有结果中：

- 目标消息 SHA、RolePlay message ID、Story/Session lineage、目标生成尝试/operation/job/request ID 是否有可信唯一绑定；
- 是否存在发送态完整模型请求载荷，是否可验证字节完整性、模型参数、模板版本、输入顺序及重试/回退发生情况；
- System Prompt、角色/世界卡版本、历史裁剪窗口及清洗结果、长期/短期记忆、事件状态及动态工具/内容注入来源；
- 输入留证的可信产生点、留存位置、完整性哈希、访问权限和时间边界；
- Response、错误/重试与最终保存 Assistant 文本之间的对应关系；有无不同尝试混淆；
- 相关已有数据库 Ledger 证据能覆盖什么，不能覆盖什么；
- A/B/C/D 等级、缺口原因码、所依据的独立证据及人工复核状态。

**第一步只审阅已经存在的档案、日志、代码/版本线索和导出能力，不把推测值写成事实，不查询生产聊天正文，不凭某种字段的存在假设完整请求已持久化。** 先输出仅聚合统计的 SAFE，再决定对少量高价值 Case 做私有的定向证据提取。

建议 SAFE 输出：`gold192_total=192`、`evidence_A/B/C/D_counts`、`unknown_evidence_count`、`request_attempt_linkage_verified_count`、`exact_sent_payload_verified_count`、`reason_counts`、`private_values_emitted=false`、`quality_v1_admitted=0`、`training_authorized=false`、`gpu_started=false`。**任何尚未逐案取证的数量一律保持 unknown，不允许把未审计的 192 条强行填入 D。**

## 4. RolePlay P0：未来请求的真实输入留证

推荐在“消息构建、裁剪、清洗、记忆注入、模型路由、最终序列化之后；HTTP/SDK 发送之前”的受控边界进行留证，并与实际已发送请求建立不可混淆的对应关系。必须考虑：

1. 一次用户操作对应多个生成尝试：attempt ID、request ID、Provider ID、模型与版本、Retry/Regeneration/Fallback 路由必须可区分；
2. 精确的有序 messages、System/Developer 信息、Tools/Tool Choice（若使用）、参数、模型与多模态引用等实际输入语义必须有可审计的表示；
3. 采集点、序列化版本、完整性 SHA256、代码版本、模板版本、动态来源版本和来源快照元数据；
4. 只在适当权限域保存敏感请求正文；使用加密、最小权限、脱敏聚合日志、明确保留周期与可验证的删除/撤回策略；不得公开保存私人故事正文或训练材料；
5. SDK/代理层可能再次转换请求：应记录链路版本及最接近 Provider 出站的请求表示，区分“准备发送”与“已提交”；不得仅以中间 Prompt Build 日志声称实际调用；
6. 响应回执、最终保存的 Assistant 消息、失败/中断/重试结果与每次 attempt 唯一关联；不把未完成的流式 partial 当作最终目标文本；
7. 提供只读、权限受控的按目标消息/尝试查询和导出接口，返回输入留证及其完整性/来源证明；无证据时返回明确 HOLD 原因，不用数据库当前快照代替。

该机制默认对**上线后的新请求**负责。历史 Gold192 仍需逐案证据审查，不得宣称新机制可以自动修复既有缺失。

## 5. R60 当前代码与阻断门槛如何处理

- 保留原 R60 Pilot7 身份核验、Ledger 计数、只读角色检查和 T1 代码审计成果，作为数据库历史证据与 RolePlay P1 加固成果。
- **保持** `r60_gold192_history_recovery_v3.py` 的 `LEDGER_TEMPORAL_ORDER_AUDIT_REQUIRED` fail-closed：它仅适用于该工具的“按 Ledger 恢复完整历史”的功能，不代表所有新的输入证据审查工具必须经过同一 Ledger 门槛。
- 新的证据发现/分类应为**独立、只读、CPU-only、SAFE-first**的工作流；不能靠跳过 Ledger guard 后继续使用未认证的旧恢复输出。
- B 类若只能恢复数据库对话，却不能证明运行时裁剪、记忆、System Prompt、路由、重试及输出关联，继续 C/HOLD。
- 任何 A/B 级别仅表示某些输入证据已经满足相应门槛，Quality-v1、Owner 审批与训练授权依旧分别判断。
- R50 Held-out 保持隔离；冻结 Gold192、Reviewer A/B、Stage72 和所有私有源文件不变。

## 6. 交付与验收顺序

1. **StoryForge P0：** 现有证据来源 inventory + 192 条逐案可用性预筛（unknown 允许）；先出 SAFE 聚合缺口矩阵，确认可以核实的实际输入记录在哪里。
2. **RolePlay P0：** 真实出站请求留证及输入—attempt—输出关联设计，经安全和隐私评审后分阶段实现；先验证“同请求重试变更、裁剪、记忆、模型回退”五类场景的留证正确性。
3. **StoryForge P0：** 优先对有强证据的少量候选做私有逐案比对和 Quality-v1 后续审核；不等待全面 Ledger 审计。
4. **RolePlay / StoryForge P1：** 对 C 类有实质收益的范围推进 Ledger 状态语义、事务顺序、Trigger、历史版本/Retention 及写入路径回归。
5. **训练门槛不变：** 冻结已批准数据、完成 QA/世界隔离/曝光和 CPU Token/Collator 验证，**单独取得用户 GPU 训练授权**后才运行。

**当下状态：** 尚未进行 Gold192 的 A/B/C/D 实证逐案分类，因此 A/B/C/D 计数均为 unknown。 `quality_v1_admitted=0`、`training_authorized=false`、`gpu_started=false`、`database_modified=false`。
