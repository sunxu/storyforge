# StoryForge — 上下文消融实验：新 Agent 接手提示词

2026-11-27 · 现行任务书 v2.1 · PR #44（未合并）。以下可直接复制给接手 Agent。

---

你是 StoryForge 的下一任执行 Agent。仓库 https://github.com/sunxu/storyforge 。唯一产品目标：让 Qwen/Qwen3.8-27B 中文互动叙事质量可证明优于 Base。不要偏离主线，不要重复开发，遵循最小化原理、最短实现路径。

## 1. 接手基线（只读）

- 先读取仓库 `AGENTS.md`，再读取 PR #44 当前 HEAD 的 `docs/plans/STORYFORGE_CONTEXT_ABLATION_TASKBOOK_20261127_CN.md` 和 `docs/REUSABLE_ASSET_INDEX.md` 顶部当前优先资产；本提示词与该任务书是唯一现行入口。实查 main 为 `5de5f81f1db1724419dc699c815ae4e042639b17`（接手时核对），历史固定归档 `15462b8779401833a5014846bc57318dd6bc1b1c`。文档 PR 分支 `docs/new-source-quality-mainline-20261126` 尚未合并，不当作 main 已有代码。
- 旧 v1.25 新来源任务书、旧交接提示词均已归档，只作必要证据查阅，不作为待办清单，不重做旧筛选、补证或技术预检。
- 保留原有安全规则和授权：不得读 R50 密封正文、不得把已暴露 Gold48/E1/E4 或评估预留 E2 转成训练；221/T、World04/Common2 等 HOLD 不改，不重复申请已经批准的平台内容使用权，不假定其它操作已授权。R60 NO_PROMOTE，R61 未启动。

## 2. 已完成的事实（无需重做）

1. R60 Base336 293 Train / 43 Val、37 步工程成功；Gold48 未证实稳定优于 Base，连续性 -0.146、互动推进 -0.083；相对 R54 分别 -0.167、-0.198。训练输入缺 System、历史仅3条；不是已证实的退化原因。旧模型在数据及梯度累积等方面不匹配，不是单变量对照。
2. 多轮新来源发现未产出正式准入样本，World04 一条质量双PASS和 Owner 批准仍来源隔离 HOLD，Common2 两条质量/CPU 已通过但准入 HOLD。唯一收藏属于 E2 预留评估来源。停止这些路线的重复查库、补证、模型审核和新故事/Teacher 生成。
3. 已直接用 HF 只读插件读取 R54 固定原运行 Stage 两份 compiled JSONL，在内存复算 SHA256 与冻结 R53 正式私有发布匹配：Train 31（308291 bytes）、Val 9（69938 bytes），历史长度4–12条，全部使用同一R27通用无卡System；40/40末三历史是 User/Assistant/User，40/40保留System及末四消息后目标SHA一致。未写派生文件、未访问新故事、未调用模型。原始40条 CPU 实审报告状态全部 REAL_LAST_ASSISTANT_AND_COLLATOR_PASS；不重复原始臂校验，不把证据移用于短臂。
4. 这只是构造可行性，并非已生成短臂、历史 actual-sent 请求已验证、原 R54 的随机性可复现或质量已改善。R54 旧31/9曾有单独正式私有发布与历史训练权限；不等于当前派生发布/训练已批准。

## 3. 唯一下一任务

只读定向核查能否复用 R54 checkpoint-16 作为原始历史臂 A；并确认现有固定诊断输入和配对评估能力是否适合本实验。

- 首先查固定归档的 `configs/v03_r54_qlora_31_9_16step_v2.yaml`、`docs/evidence/V03_R54_TRAINER_STATE_LOSS_SUMMARY_20261022.md`、`docs/evidence/V03_R54_V2_GPU_OWNER_COMPLETED_PRE_INTAKE_20261021.md`、`docs/V03_R54_HF_GPU_V2_SYNC_SUBMIT_VERIFY_CN.md`、必要的原实际运行配置/回执（仅已知原运行路径）。只核对模型 revision、模板、软件、有效参数、seed/data_seed、采样顺序、步数、终态 checkpoint 是否可用；无证据则记录未知，不做无限追溯，不下载大权重，不提交 Job。
- 核对现有 Gold48 诊断包和 `docs/R60_GOLD48_OWNER_LOCAL_RUNBOOK_20261121_CN.md`；先确认固定输入可用性和使用范围，不生成问题、不调用评审、不把旧题当独立新测试、不为此读取 R50。
- 最小实验固定 R54 原31/9及顺序，A 原4–12条历史，B 原末三条历史，System/目标/训练设置相同；两臂从同一 Base 起点、匹配 seed 和顺序。固定终末 checkpoint 和相同推理输入/采样，不用不同 Val loss 选不同 checkpoint。只改变训练历史窗口（同时影响信息量/token数），不恢复历史卡、不机械加长输出、不并行测试其他变量。
- 根据证据提交明确选择：可匹配时拟复用旧 A、只训练 B；无法匹配则提出匹配双臂或明确探索性单臂/停止，不冒称严格因果。不要为了复用旧 A 而补造参数；旧 R54 runner 固定原SHA，不直接用于新输入。

## 4. 交付与停止条件

本次实际交付应为短而可执行的裁决，不是继续制作文档模板或新工具：

```text
对照执行选择：复用 A / 匹配双臂 / 探索性 / HOLD
实际已证：数据、模型、参数、随机性、checkpoint、诊断输入（逐项）
实际未证：仅影响本次选择的缺件
拟执行：原31/9固定、单变量窗口、真实短臂CPU mask、固定评估范围
预算：CPU/GPU/推理/Reviewer 调用数量与费用上限（未知明示）
验收：连续性、互动推进、玩家自主权及其余六维/三严重标记
停止条件：缺必要权限/证据、对照失效或效用不足
新增代码：默认0；若真有缺件，说明已查路径和最小复用差距
```

优先复用 `src/storyforge_dataset/hf_runtime/`、`src/storyforge_dataset/generation_eval/`、`scripts/hf_label_mask_audit.py` 及原 SFT/评估 Skill，均先查 main 与固定归档。不得建立新数据管线、验证器、审核框架或迁移整个分支；没有具体缺件不开发。固定输入、历史质量诊断、保护范围不用反复核查。

本轮只读调查和实验提案已授权，不等于派生数据发布、HF CPU/GPU、模型推理、付费评审、外发、训练、部署或晋升授权。另行批准后才冻结新私有短臂并实际 CPU 验收，再考虑训练；不重复原字节已有 PASS。正式质量结论最终仍需独立未暴露评估。任何实验不得冒充正式 Gold 或自动改变现有门禁。

保持 `quality_v1_admitted=0`、`train_admitted=0`（当前新来源）、`training_authorized=false`、`model_promoted=false`、`r61_started=false`。私有数据仅在获准私有域处理，Git/聊天只放 SAFE 聚合；不提交正文、逐案标识、凭据、权重或私有报告。所有工作遵循最小改动、最短路径：如果已有证据足够，立即裁决并提出下一次明确执行授权，不循环扩大调查。

---
