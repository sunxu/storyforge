# StoryForge R60 P4 Profile Freeze Review — Owner 裁决包（2026-11-10）

> **状态：OWNER_REVIEW_READY__PROFILE_NOT_FROZEN**
>
> 本包用于 Owner 对不可变 Generation Profile 做最终裁决。它不自动修改 Profile 授权，不启动 Job、GPU、Inference 或 Training。当前四项生产授权仍全部为 false。

## 1. 裁决摘要

P4 配置候选、采样实验设计、Prompt/Schema、运行镜像和依赖锁已通过 CPU-only Freeze Review；Worker CLI / Bootstrap 也已通过固定 Linux/amd64 镜像的真实 CPU-only 入口验收。

建议 Owner 将本包所列配置作为**Profile Freeze 候选**审阅。若批准，只批准配置冻结和不可变 Profile SHA；不同时批准任何推理、GPU、私有数据访问、Development20/Locked30 执行、1000 条审核或训练。

## 2. 当前 GitHub 证据

| 项目 | 证据 |
|---|---|
| 仓库 / 分支 | `sunxu/storyforge` / `r60/p4-generation-eval-framework` |
| PR | [#30](https://github.com/sunxu/storyforge/pull/30)，Open / Draft |
| Issue | [#28](https://github.com/sunxu/storyforge/issues/28)，OPEN |
| 本包首次生成提交 | `59b753f82f77067e6ff8cac6cb0cf135a6f9e276`（后续文档提交会推进 HEAD；Owner 裁决时须实时读取 PR #30 head SHA） |
| 最近工程代码 HEAD | `7e9fdf9b47aee8da02ceeee1babc7a67d2ee6be9` |
| 代码 HEAD 后续差异 | 仅文档更新；无源码、测试或 Workflow 变化 |

### 2.1 代码 HEAD 对应 Actions

| Workflow | Run ID | 结果 |
|---|---:|---|
| Repository CI | `42810266068` | completed / success |
| R60 Generation Eval CI | `42810265927` | completed / success；49 passed |
| P4 Runtime Image Candidate | `42810265919` | completed / success |

P4 Runtime Image Candidate 在固定容器内实际完成：
1. 固定 Commit 的 GitHub codeload source archive 下载；
2. Bootstrap 安全解压；
3. 真实 `pip install --require-hashes`（不是 dry-run）；
4. `worker_cli --help` 参数解析；
5. 未授权 Profile 的 CLI fail-closed；
6. 禁止 torch / transformers / huggingface_hub 导入及 CLI 阶段网络访问。

Bootstrap 负向归档测试覆盖：路径穿越、符号链接、FIFO 特殊文件、成员数量上限、下载字节上限、解压内容上限；均在 55 项 CPU-only 测试中执行。

容器 SAFE：
- schema：`storyforge_r60_worker_cli_container_smoke_safe_v1`
- status：`CPU_CONTAINER_ENTRYPOINT_FAIL_CLOSED_PASS`
- `bootstrap_archive_executed=true`
- `dependencies_installed_with_hashes=true`
- `cli_help=true`
- `unauthorized_profile_rejected=true`
- `runtime_imports_blocked_and_not_attempted=true`
- `network_blocked_and_not_attempted=true`
- `output_directory_created=false`
- `private_values_emitted=false`
- `inference_started=false`
- `gpu_started=false`
- `training_started=false`

### 2.2 CPU-only Freeze Review SAFE

- status：`P4_FREEZE_REVIEW_READY_NOT_FROZEN`
- `ready=true`
- `blockers=[]`
- nested sampling status：`SAMPLING_DECISION_VALID__PROFILE_FREEZE_PENDING`
- `ready_for_profile_freeze=false`
- `private_values_emitted=false`
- `inference_started=false`
- `gpu_started=false`
- `training_started=false`

Artifact：`r60-p4-freeze-review-safe`  
Artifact ID：`13763895951`  
ZIP SHA-256：`25b568029272a4e48f4a75c755a98f83a706583f3bf6a61915ebb257065f1d0b`

解释：`ready=true` 表示候选配置与评估契约通过 CPU-only Review；`ready_for_profile_freeze=false` 与 `P4_FREEZE_REVIEW_READY_NOT_FROZEN` 表明它没有替 Owner 做出冻结决定。

## 3. 候选 Profile 固定内容

机器可读候选：`experiments/r60_quality/p4_generation_profile_candidate_v1.json`  
状态：`P4_PROFILE_CANDIDATE__NOT_FROZEN`

### 3.1 三模型 Revision / Tokenizer / Template

| Role | 模型 / Revision | Tokenizer SHA-256 | Template SHA-256 | Generation Config SHA-256 |
|---|---|---|---|---|
| A | Qwen/Qwen3-32B / `9216db5781bf21249d130ec9da846c4624c16137` | `aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4` | `a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8` | `2325da0f15bb848e018c5ae071b7943332e9f871d6b60e2ed22ca97d4cb993d2` |
| B | zai-org/GLM-4-32B-0414 / `8dea913c41b543527c2860fb6f3c15c202f24aeb` | `76ebeac0d8bd7879ead7b43c16b44981f277e47225de2bd7de9ae1a6cc664a8c` | `db700f25fa300e53634c6fc78dee86b7fbd6d27e624edb855b18a4078c83a822` | `56ee0be8c595f22a6a80a822096533e10455fcd1e859e0fc36a6e760088147fa` |
| Challenger | zai-org/GLM-Z1-32B-0414 / `8eb2858992c1f749e2a6d4075455decc2484722d` | `76ebeac0d8bd7879ead7b43c16b44981f277e47225de2bd7de9ae1a6cc664a8c` | `adee3accece2e4a347280cb16580b3575d6164f2a0f4ac58a1a8392a346eb241` | `56ee0be8c595f22a6a80a822096533e10455fcd1e859e0fc36a6e760088147fa` |

完整 18 个 Tokenizer/Config/Template 文件 SHA 清单绑定在 P4 candidate 的 `tokenizer_file_hashes`。以上模型 Revision 不得自动升级。

### 3.2 Sampling / Thinking 决策

| Role | Locked30 primary | Development20 arm | Thinking |
|---|---|---|---|
| A / Qwen3 | sampling：`do_sample=true, temperature=0.6, top_p=0.95, top_k=20, min_p=0` | 同 primary | `enable_thinking=true` |
| B / GLM-4 | sampling：`do_sample=true, temperature=1.0, top_p=1.0, top_k=50` | 同 primary + greedy sensitivity | pinned template default，不额外注入 prefix |
| Challenger / GLM-Z1 | greedy：`do_sample=false` | 同 primary + sampling sensitivity（`0.6/0.95/40`） | 显式 `<think>` generation prefix |

- Base seed：42；per-sample effective seed = base seed + stable input index。
- Development20 用于主配置与敏感性对照；Locked30 仅 primary，不得调参。
- GLM-4 与 GLM-Z1 同属 GLM4 架构家族，不作为两个独立模型家族投票。
- 以上采样是 Owner 已接受的实验设计，不代表推理效果已经验证。

### 3.3 Prompt / Output Schema

Owner 已批准 Prompt v1 与 Output JSON Schema v1：
- Prompt SHA-256：`51465853db6a2b61a9f87b1e9d5f23f7f02bd2c98b5a0d6a8ab2ec61322346e1`
- Schema SHA-256：`e6371bf3319affcae190b6ccb9a1b8ce778bae440a91eefe39a65b2586930d70`
- Rubric：`r60_severity_rubric_v2_1`

批准仅覆盖 Prompt 与 Schema 的内容哈希，不包含 Profile Freeze 或推理授权。

### 3.4 Stop / Token Budget

- Context ceiling：32,768 tokens
- Input budget：28,672 tokens
- Generation budget：4,096 tokens（包含 reasoning）
- 超出输入预算：拒绝，不静默截断。
- EOS IDs：A `[151645,151643]`；B / Challenger `[151329,151336,151338]`。
- PAD IDs：A `151643`；B / Challenger `151329`。
- finish reason：`eos` / `length` / `unrecognized_stop`；无法识别时 HOLD。

### 3.5 Runtime / Dependency

- Image：`docker.io/pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee`
- Platform：Linux/amd64
- Python：3.11.11
- PyTorch：2.6.0+cu124；CUDA build 12.4
- Transformers：4.57.1
- Dependency lock：`requirements/hf-generation-eval.lock`
- Lock SHA-256：`81b0006536695f1552161302515f1f154d65b3b32a8520a34e774b4e518ceb4c`

## 4. 32K 显存 / 运行时间 / 费用审阅

完整计算、假设和证据等级见 [P4 32K Resource Budget](R60_P4_32K_RESOURCE_BUDGET_20261110_CN.md)。

关键结论：
- 真实短输入 A100 Smoke 峰值 allocated：Qwen 61.05 GiB；GLM-4 / GLM-Z1 约 60.67 GiB。
- 32K batch=1 BF16 KV cache 理论值：Qwen 8.00 GiB；两个 GLM 约 1.91 GiB。
- 以上相加仅是粗估，不包含长 prefill 临时峰值与碎片；A100 80GB 对 Qwen 余量不足，不作为首选。
- 首选候选：1x H200 141GB，$5/GPU-hour（执行前重核价格）。
- 单模型硬超时 60 分钟；三模型串行首阶段最多 3 GPU-hours / $15。
- 后续 synthetic pilot 另计最多 6 GPU-hours / $30；失败定位预留最多 2 GPU-hours / $10；整个预算封顶 $55，分阶段批准。
- 32K 实际显存、prefill、decode 和耗时尚未测试。当前 HF GPU 消耗 0 GPU-hours，费用 $0。

## 5. Owner Mac CLI Runbook

Owner 可按 [P4 Owner Mac CLI Runbook](R60_P4_OWNER_MAC_CLI_RUNBOOK_20261110_CN.md) 执行固定镜像的 CPU-only `--help` 与未授权 Profile fail-closed 检查。

Owner 2026-11-10 已提供实机自检回执：`OWNER_MAC_CPU_FAIL_CLOSED_SELFTEST_PASS`。CLI 参数入口、预期 exit-code=2 / `GENERATION_PROFILE_NOT_AUTHORIZED`、未创建输出目录的 Runbook 断言通过。回执 SAFE 为 `GENERATION_WORKER_HOLD`，其中 `gpu_started=false`、`inference_started=false`、`training_started=false`、`private_values_emitted=false`。这是**正确拒绝未授权配置**，不是授权模型生成成功。Owner 回执没有单独附上 Git SHA / docker inspect，因此这些只能保持未独立核实。本次未执行 HF Job。

## 5.1 Owner Mac 回执的审计边界

- `usage: worker_cli.py ... --model-role {A,B,challenger}`；
- SAFE schema：`storyforge_r60_generation_worker_receipt_safe_v1`；
- SAFE status：`GENERATION_WORKER_HOLD`；
- reason_code：`GENERATION_PROFILE_NOT_AUTHORIZED`（预期 fail-closed）；
- `OWNER_MAC_CPU_FAIL_CLOSED_SELFTEST_PASS`；
- Runbook 的逐项脚本断言要求退出码 2 且目标输出目录不存在。
- 证据来源为 Owner 本次手工回传；没有新增 HF Job、GPU、Inference 或 Training，也没有提供本地 Git SHA、镜像 inspect 原始回执。

## 6. 未解决 HOLD（必须在批准后仍保留）

1. **Owner Mac CLI 实机 SAFE**：Owner 已回传预期 fail-closed PASS；尚缺独立的本地 Git SHA / 镜像 inspect 原始输出。CPU 拒绝路径完成，但不代表 GPU 模型生成。
2. **P4 私有输出路径**：历史 Owner Mac CLI 对 Bucket RW 曾成功，但本轮未提交 HF Job；本 P4 Job 的输出卷与 SAFE 回收闭环没有新实测。HF 连接器问题继续暂停，不由 ChatGPT 探测。
3. **32K 真实运行能力**：目前只有短输入 A100 Smoke 与理论 KV cache 估算；没有长上下文 GPU 实测。H200 是候选，不是已验证硬件。
4. **生成行为边界**：当前 Smoke 不覆盖 28,672/4,096 长上下文，不代表真实评估输出结构、Thinking 长输出和 finish_reason 在完整预算下已验收。
5. **正式执行授权**：所有生产授权继续 false。

这些 HOLD 不得通过更改 SAFE 文本或将历史 Smoke 授权复用来关闭。

## 7. Owner 裁决

请 Owner 明确确认以下两层决定，彼此独立：

### A. Profile Freeze（本包请求的决定）

是否批准将当前候选 Profile 按上述模型 Revision、Tokenizer/Template/Generation Config fingerprints、sampling、seed、Prompt/Schema、stop/EOS、token budget、runtime digest 与 dependency lock SHA 冻结为不可变版本？

若批准，只执行：
- 将 Profile Freeze 授权按独立流程变更为 true；
- 生成不可变 Frozen Profile 文件与 SHA-256；
- 记录 Owner 裁决及时间。

### B. 生产执行授权（本包不请求、不包含）

以下全部保持 false，必须另行授权：
- `inference_authorized=false`
- `gpu_authorized=false`
- `training_authorized=false`

本包不授权 Development20 / Locked30 推理、真实私有案例读取、1000 条审核、SFT、GPU Job、HF Bucket 探针或任何额外运行。即使 Owner 批准 Profile Freeze，也不代表上述能力自动获准。

## 8. 本包状态

`OWNER_REVIEW_READY__PROFILE_NOT_FROZEN`

Owner 裁决前：
- `profile_freeze_authorized=false`
- `inference_authorized=false`
- `gpu_authorized=false`
- `training_authorized=false`

PR #30 保持 Open / Draft；Issue #28 保持 OPEN；不自动合并。
