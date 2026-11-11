# StoryForge R60 GLM 全量25条下一 Agent 启动提示词（可复制）

以下正文可原样发送给新的 ChatGPT Agent；本文也是交接包的一部分。

---

你现在接手 GitHub 仓库 `sunxu/storyforge` 的 **R60 GLM-4 B25 Generation Snapshot + CPU Replay 完整25条评审工程**。

## 你的目标

以 GitHub 当前真实状态为准，**完成 Owner Mac 上的全25 CPU preflight 与完整 H200 生成的交付准备**，由 Owner 在 Mac CLI 自行执行**一次完整25条 GLM 生成**，全部保留成功返回的原始模型输出快照，逐条保留冻结 Reviewer 新 Checkpoint 或技术失败回执。得到 Owner 的真实执行回执后，完成25份快照的身份/完整性验收和 `--full25` CPU Replay，汇总真实 Quality-v1 技术有效性与质量决定；不得直接将 Replay 技术有效视为训练准入。

**强制要求：取消1条或2条试跑上限。** 这是新的独立原始25条审查，**不是**失败12条子集隔离重试。你不应建议用户先单条运行；只有出现真实安全阻塞时才停止。旧13个有效及12个失败回执必须永久保留，新运行写独立目录。

## 第一优先级：读取 GitHub 当前权威文档

1. [R60 GLM 全25下一 Agent 权威任务书](https://github.com/sunxu/storyforge/blob/r60/p4-generation-eval-framework/docs/R60_GLM_FULL25_NEXT_AGENT_HANDOFF_20261111_CN.md)
2. [Owner Mac 全25执行手册](https://github.com/sunxu/storyforge/blob/r60/p4-generation-eval-framework/docs/R60_GLM_FULL25_SNAPSHOT_OWNER_RUNBOOK_20261111_CN.md)
3. [Snapshot + CPU Replay 历史与机制](https://github.com/sunxu/storyforge/blob/r60/p4-generation-eval-framework/docs/R60_GENERATION_SNAPSHOT_CPU_REPLAY_20261111_CN.md)
4. [GLM/Qwen 旧诊断历史](https://github.com/sunxu/storyforge/blob/r60/p4-generation-eval-framework/docs/R60_GLM_QWEN_REPAIR_TRACK_20261111_CN.md)

别依赖本文的静态 HEAD 推断现状。实时核对工作分支 `r60/p4-generation-eval-framework`、PR #30、Issue #28、最新 HEAD 和四组 CI。代码运行固定版本 `6f2a71f12f3a2408b4082d6f8b86e69e0b5cf384`，废弃有参数冲突的 `77da8093c831a6cb3771385b1c673ffb82143529`。若你需要修复实际代码，补合成测试、通过 CI，再给 Owner **新的完整代码 PIN**；否则沿用现有 PIN，不要把仅文档更新当作代码变更。

## 已确认与未确认

已确认：冻结输入25条、GLM revision 与原 Runner 身份固定；完整25参数入口/原始位置1..25回放/一次 vLLM 引擎/逐条技术失败隔离/独立 Snapshot/合成回归均已实现，代码 PIN 对应四组 CI PASS。Owner 提供过 `GLM_FROZEN_SNAPSHOT_CPU_REPLAY_PREFLIGHT_PASS`，该回执是**真实冻结 Runner + 合成单条 Snapshot**的 CPU 验收。

**尚未确认**：新版 `--full25` Owner Mac CPU preflight、一次真实 H200 25条 Job、25个真实 slot01 快照、25份新 Checkpoint/技术失败回执、真实 FULL25 CPU Replay。不要虚构这些已经 PASS。

模型：`zai-org/GLM-4-32B-0414`，revision `8dea913c41b543527c2860fb6f3c15c202f24aeb`；原输入 SHA `01639568cf21a7b98356f2b3b74f567943b4a6844edb9230b58759789ab67fc9`；代码 PIN 如上；固定 vLLM 镜像 digest 以 Runbook 为准。

## 具体执行任务

**P0，先完成**：GitHub 实时核验；从运行代码 PIN 生成完整且同源的 Mac staging 脚本/命令，验证冻结 `runner.py` 和25条 `source.private.jsonl`；执行 `r60_glm4_snapshot_cpu_preflight.py --runner ... --input ... --full25`，只在真实 SAFE PASS 时进入付费生成准备。不要混用历史 v1/v2 工具文件或历史输出。

**P1，准备 Owner 手动启动**：给出完整可复制的 `hf jobs run --namespace adradar --flavor h200 --attempts 1 --timeout 2h --detach` 命令及固定镜像/挂载/入口：
`bash /input/r60_glm4_full25_snapshot_entrypoint.sh RUN_ID`。
入口应使用 `--snapshot-full25 --isolate-technical-failures --case-limit 25`，并提供独立的 `--generation-snapshot-dir`，**不得**设置 `--snapshot-probe-cases`、`--literal-probe-cases`、`--retry-baseline-dir`、`--resume`、`--snapshot-primary-only`、`--quote-literal-repair`。RUN_ID 必须唯一，两个 Bucket 输出目录必须不存在，不能清除或覆盖旧回执。ChatGPT **不调用 HF Jobs 提交**，由 Owner Mac 自己执行。

**P2，基于 Owner 的真实 HF Job/SAFE 回执验收**：判断是否 `ALL_CASES_ATTEMPTED.attempted=25`、`SNAPSHOT_FULL25_SUMMARY.attempted=25`，25份主生成快照均可逐文件验签，25条均有**恰好一个**新审核 Checkpoint/白名单技术失败回执，`verified + technical_failures = 25`。技术失败可能使 exit42，这不必然意味着留证失败；但出现非预期异常、预算不足、缺失/损坏 Snapshot/回执，必须宣告 PARTIAL/HOLD。严格保存已完成的证据，不能无条件重跑。

**P3，CPU 回放**：仅在拿到真实快照后运行 `r60_glm4_snapshot_replay.py --full25`。报告要 `scope=FULL25` 且 `replayed_cases=25`，并明确严格冻结校验、标点级实验修复的不同技术结果；质量 PASS/HOLD/REJECT 只能来自实际有效决策。CPU Replay 绝不自动写 Quality-v1 训练准入。

**P4，收尾**：更新 GitHub 代码/文档/Issue #28 与 PR #30 评论（不要合并），给出完整运行日志中可公开的 SAFE 汇总、验证数字、失败说明和下一阶段建议；优先利用同一批 Snapshot 做 CPU Debug，避免新一轮 GPU 重复生成。

## 资源与安全边界

仅由 Owner Mac 手动提交付费 HF GPU/云 Jobs；不能通过 ChatGPT Hugging Face 连接器提交，之前存在 Bucket RW 403。不要要求用户提供长期 PAT/DSN，不改 Bucket ACL；不泄露私有原文、生成正文、ID Map、密钥到 GitHub 或 SAFE 日志。所有新输出独立且不可覆盖。冻结 Runner、输入、Rubric v2.1、原有13+12回执均不可改变。此任务不授权 SFT、1000条批量审核、其他模型 GPU 工作；`quality_v1_admitted=0`、`training_authorized=false` 直至另有审批。

## 首次回复的要求

不要泛泛重复计划。立即核验 GitHub 真实 HEAD/PR/四组 CI，检查运行 PIN 及全25相关实现。明确可运行/存在的阻塞项，提供 **可复制的 Mac 全25 CPU Preflight 与 H200 staging/运行命令**，告知用户应回传哪些 SAFE 字段与验收数字；不要要求用户重复已经确认的背景信息，也不要建议重跑1条试验。执行中如果发现真正的代码阻塞，直接修复 GitHub、增加测试、核验 CI 后再交付新 PIN 和命令。未执行的步骤不得写成 PASS。

---

**注意**：以上是可复制的提示词正文；新 Agent 仍须以 GitHub 实际状态为准。
