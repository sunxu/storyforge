# StoryForge R60 新 Agent 接手提示词：P4 Worker CLI 工程验收

你现在接手 `sunxu/storyforge` 的 R60 P4 后续工作。请先完整阅读：

1. [P4 下一阶段接手任务书](R60_P4_NEXT_AGENT_HANDOFF_TASKBOOK_20261110_CN.md)
2. [P4 Generation Eval Framework](R60_P4_GENERATION_EVAL_FRAMEWORK_20261110_CN.md)
3. [P4 Generation Evaluation Plan](R60_P4_GENERATION_EVALUATION_PLAN_20261110_CN.md)
4. [P4 Runtime and Stop Policy](R60_P4_RUNTIME_AND_STOP_POLICY_20261110_CN.md)
5. [HF 连接器故障历史记录](R60_HF_CHATGPT_JOBS_CONNECTIVITY_20261110_CN.md)

## 当前接手目标

继续完成 Worker CLI / bootstrap 的 CPU-only 端到端工程验收、Owner Mac CLI 执行包、32K 长上下文资源预算和最终 Profile Freeze Review 材料。**不要重新开展 P0/P1/P2/P3，不要重复短输入 GPU Smoke，不要等待或排查 ChatGPT HF 403。**

## 启动必须先做

- 实时读取仓库分支 `r60/p4-generation-eval-framework`、PR #30、Issue #28。
- 获取当前 HEAD，并核对这个精确 SHA 对应的 Repository CI、R60 Generation Eval CI、P4 Runtime Image Candidate。
- 查看工作树是否干净；不 reset、不 force-push、不 merge、不关闭 PR。
- 记录当前 SHA 后再开始任何修改。不能沿用任务书中的历史 CI 结果替代新 HEAD 的结果。

## 已有基线（不要误报为待开发）

在已核验 HEAD `a1db1ac70fd3777d78460eee58e7d2b891867c40`：
- 三项 CI 均 PASS：Repository CI（1010 passed / 5 skipped / 42 subtests）、Generation Eval CI、Runtime Image Candidate。
- Worker CLI `python -m storyforge_dataset.generation_eval.worker_cli` 已实现。
- bootstrap 从固定 GitHub Commit 下载源码归档并安全解压；hash-locked dependencies 使用 `--require-hashes`。
- digest-pinned 镜像 Linux/amd64：Python 3.11.11、torch 2.6.0+cu124、CUDA build 12.4；lock dry-run hash install PASS。
- CPU-only Freeze Review：`P4_FREEZE_REVIEW_READY_NOT_FROZEN`，ready=true、blockers=[]；并非 Profile Freeze。
- P3 CPU preflight PASS；此前经单独授权的短输入三模型 GPU Runtime Smoke 3/3 PASS。

## 立即执行的工作

按任务书 P4-A → P4-B → P4-C → P4-D 顺序：

1. 补齐 Worker CLI fail-closed、manifest/input/hash/token-budget、runtime/lock mismatch、输出 create-only/0600、bootstrap archive 安全边界等测试。
2. 增加真实 CPU-only digest-pinned container entrypoint self-test。不得下载模型权重、启动 GPU、执行 inference；FakeBackend 只用于合成测试。
3. 提供 Owner 可复制的 Mac CLI 自检与 HF 执行指令。HF Job 如需执行，只由 Owner 在 Mac CLI 执行；你不提交 HF Job、不测试 Bucket。
4. 形成 32K（28,672 input + 4,096 generation）显存/耗时/费用预算，清楚区分实测与估算。
5. 汇总最终 Profile Freeze Review 包，等待 Owner 决策。

## HF 暂停指令（不可违反）

Owner 已决定暂停 Hugging Face 403 / OAuth / Bucket RW 排查。ChatGPT 和你不得提交 HF Job、测试 Bucket、修改 OAuth/scope/ACL/Trusted Publishers、切换个人 namespace 或索取长期 PAT。只提供复用代码、命令、验收标准、SAFE schema 与结果分析。Owner 自行在 Mac CLI 执行 HF 任务。

## 授权边界

当前 `profile_freeze_authorized=false`、`inference_authorized=false`、`gpu_authorized=false`、`training_authorized=false`。历史 runtime smoke 一次性授权已消费。不得启动正式 Development20 / Locked30 推理、1000 条审核或 SFT；不得读取 Locked30 私有案例或上传私有正文、盲化映射、Owner labels、凭据、DSN。不得把合成测试或旧 Smoke 说成正式评估 PASS。

PR #30 保持 Open / Draft，Issue #28 保持 OPEN。每次提交后重新核验当前 HEAD 的全部 Actions，并更新任务书和 Issue。最终汇报必须列出 commit SHA、真实测试、SAFE、资源/费用、HOLD 和下一步。

现在开始刷新 GitHub 状态并实施，不要只给计划。
