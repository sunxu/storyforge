# StoryForge — 上下文消融实验任务书

**版本：** v2.0 · 2026-11-27  
**状态：** `R54_FROZEN_31_9_CONTEXT_ABLATION_FEASIBLE__DESIGN_ONLY`  
**唯一产品目标：** 使 Qwen/Qwen3.8-27B 中文互动叙事质量可证明优于 Base。Owner 已批准质量问题驱动的复盘建议；本轮是只读可行性核查及设计，不是新数据发布、HF Job、训练或生产授权。

## 1. 为什么调整

R60 Gold48 未证明稳定优于 Base，连续性差值 -0.146、互动推进 -0.083；相对 R54 为 -0.167、-0.198。原因未定。R60 训练输入无 System、仅三条历史消息，R46/R54 有通用 System；R54 与 R60 梯度累积亦不同（2 对 8），故旧模型间比较不能归因于上下文。停止重复普通会话筛选、旧留证补证、完整历史全集追查、生产留证工程和新世界发现。离线 Teacher 生成仍暂停。

## 2. 本轮实际核查结果

以 R60 冻结归档 `15462b8779401833a5014846bc57318dd6bc1b1c` 的历史输入构造、R53正式私有31/9发布、R54训练、R58主输入字节回执与历史数据血缘为依据。R46 49/15 与 R54 Train31 有23条精确目标重复（14旧Train、9旧Val），5完整消息序列相同、18不同；不据此宣称严格消融。

直接只读固定 R54 原运行 Stage 两个 compiled JSONL，内存按完整行拼接、计算 SHA256（实现通过标准 abc 测试向量）、与冻结发布哈希精确核验。实际 Train 308291 bytes/31条，Val 69938 bytes/9条，两个 SHA 均一致。全部40条仅 messages 字段、每消息 role/content，首条同一449字节R27通用无卡System（精确SHA匹配），最后均Assistant目标；分split目标哈希各31/9互异。历史长度（不计System与目标）：Train 4条历史×1、5×5、12×25；Val 5×3、11×1、12×5。40/40末三条历史均 User/Assistant/User，完整历史均多于3；内存投影保留System与末四条消息后40/40目标哈希一致。未保存、外发或输出原文/逐案ID/哈希；未运行模型或新Job。不是历史job读时对象不可变证明，不声称恢复生产实际Prompt、完整故事卡或未知历史全集隔离。

现有 R53_HF_CPU40_AUDIT_REPORT_PRIVATE.json 40/40状态 REAL_LAST_ASSISTANT_AND_COLLATOR_PASS；旧原始字节CPU证据可复用为原始臂证据，不能转移到修改后字节。R53历史正式私有发布31/9是旧用途批准，不是新派生发布或GPU许可。

## 3. 最小实验设计（尚未执行）

首先只检验**训练历史窗口长度**一个因素，而非同时变更System、故事卡、数据量、模型或训练参数。

| 项目 | A：原始历史 | B：短历史 |
|---|---|---|
| Train / Val | 原固定31/9 | 同31/9、同顺序及划分 |
| System | 同一原R27通用System | 完全不变 |
| 可见历史 | 原4–12条 | 原末三条 User/Assistant/User |
| 最终Assistant | 原目标 | 字节不变 |
| 训练配置 | 固定同一Base revision、QLoRA、模板、last_round、seed及排序 | 同左 |

短臂故意移除旧历史，是研究消融而非声称更优上下文或新Gold；先确认删除信息可能改变目标条件、无未来泄漏，记录此限制，不修写目标或补造历史卡。固定训练/验证划分及保护集边界，不拆分世界，不把历史Val用于最终测试。对同一固定诊断输入、同一推理配置比较两个训练臂，避免把不同推理上下文混入训练因素。训练/验证loss非文学质量结论。R54 旧checkpoint可作已有历史参照；仅在实际训练配置、数据字节、seed/order等可匹配时才考虑复用作严格对照，否则另行决定是否运行两个匹配臂。不直接调用写死旧SHA/31/9的R54 submit流程。复用现有共享训练、label-mask、评估工具；只在真实执行缺件出现时提最小兼容改动。

## 4. 验收与唯一下一步

**下一步：先确定对照执行口径及既有诊断输入可用性，提交一次具体实验预算/授权提案。** 原R54 checkpoint/配置/随机性证据只做定向查阅，不扩大历史审计。若不能严格复用原臂，以匹配双臂或明确探索性单臂为备选，不冒称因果结论。派生短臂实际冻结及CPU mask验收在明确批准后进行；不重跑未变化原始臂已有验收。已暴露Gold48/E1/E4仅作内部诊断，不冒充最终盲评，不作训练/选参数据；不读R50密封正文。E2仍是评估预留，保持训练排除。最终优于Base需新的独立未暴露评估验证，复用六维及严重标记，重点连续性、互动推进、自主权。先确定值得继续的效果与停止条件，报告不确定性，不把小样本探索当晋升依据。

不新建数据系统、不继续筛Supabase、不补旧HOLD、不调整221/T、不调用Teacher、不自动外发评审、不训练/部署/晋升。R60 NO_PROMOTE，R61未启动；`quality_v1_admitted=0`、`train_admitted=0`（当前新来源正式准入）、`training_authorized=false`、`model_promoted=false`。本轮新增代码、数据写入、付费模型调用、GPU/HF Job均0。

## 5. 依据与历史归档

- [R60 Gold48最终报告](https://github.com/sunxu/storyforge/blob/15462b8779401833a5014846bc57318dd6bc1b1c/docs/R60_BASE336_GOLD48_QUALITY_V1_FINAL_OWNER_DECISION_20261122_CN.md)
- [R53正式私有发布31/9回执](https://github.com/sunxu/storyforge/blob/15462b8779401833a5014846bc57318dd6bc1b1c/docs/evidence/V03_R53_FORMAL_PRIVATE_31_9_RELEASE_OWNER_RECEIPT_ACCEPTED_20261021.md)
- [R54固定配置](https://github.com/sunxu/storyforge/blob/15462b8779401833a5014846bc57318dd6bc1b1c/configs/v03_r54_qlora_31_9_16step_v2.yaml)
- [历史训练血缘](https://github.com/sunxu/storyforge/blob/15462b8779401833a5014846bc57318dd6bc1b1c/docs/evidence/V03_THREE_GPU_TRAININGS_EXACT_DATA_LINEAGE_PRELIMINARY_20261022.md)
- [历史主输入字节回执](https://github.com/sunxu/storyforge/blob/15462b8779401833a5014846bc57318dd6bc1b1c/docs/evidence/R58_G1_R46_R54_HF_PRIMARY_INPUT_OWNER_MAC_SAFE_RECEIPT_20261031.json)
- [旧任务书 v1.25（完整历史，不作现行任务队列）](https://github.com/sunxu/storyforge/blob/739b2fac76ee7efed45c4dce855a4d37a17f2691/docs/plans/STORYFORGE_NEW_SOURCE_QUALITY_MAINLINE_TASKBOOK_20261126_CN.md)
- [可复用资产索引](../REUSABLE_ASSET_INDEX.md)
