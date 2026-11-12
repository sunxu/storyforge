# StoryForge R60 — Common2 HF CPU2 下一Agent权威交接任务书

> **2026-11-12 最新权威覆盖声明：Common2 CPU技术验收已PASS（优先于以下全部旧“IMAGE_FIX_HOLD/Collator未知”段落）。** 第五轮真实HF Job `6af570089737d9a9e093d501` 已 `COMPLETED`，Worker输出 `R60_CPU2_V2_REAL_COLLATOR_PASS__R50_TRAIN_HOLD`；已验证两条实验输入的Tokenizer、严格R18 Label Mask、实际ms-swift Collator。**不再执行下文任何旧Submit、重试、Stage重建命令**。当下只读验签既有SAFE回执、分析原生/Swift模板不等价、核验完整R50排除、形成Owner训练准入决策；`SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT`、`native_template_token_parity_verified=false`、`r50_complete_exclusion_verified=false`、`train_admitted=0`、GPU/SFT HOLD。环境和可复用命令详见 [HF Jobs Mac CLI CPU2实战手册](standards/HF_JOBS_MAC_CLI_CPU2_PLAYBOOK_20261112_CN.md)。本覆盖声明只更新Common2，不替代其他Agent并行状态。

> 2026-11-12；以GitHub目标分支当前HEAD、Owner私有SAFE回执及最新只读现场核验为准。本文件是**交接材料**，不是授权新Agent立刻提交Job。

## 一、目标、当前结论与最重要的纠错

**项目主线是从冻结Real1000中形成有质量证据、来源绑定、可复现且经R50隔离和CPU真实Collator验证的SFT训练样本。** 不要把修HF Job当作独立目标，不扩大到生产环境、GPU训练或新日期批次数据。

最近一次比“SDK修复已提交”**更新**的Owner实际执行回执：
`{"status":"R60_COMMON2_CPU2_IMAGE_FIX_HOLD","reason_code":"SAFE_REMOTE_OR_RUNTIME_HOLD","train_admitted":0,"private_values_emitted":false}`。
这表示 SDK修复脚本**没有返回新Job ID**，但该合并错误码**不能证明HF服务端未创建Job**。必须只读核查是否留下再次提交标记、旧Job状态和新Job事实。**绝对不可自动再提交、清理标记、重新同步数据。**

首次Owner CLI提交的Job ID `6af53990ab34849891aecb44` 已出现终态 Error，服务端错误为`Job image specification error ... docker.io/--name`：镜像参数解析失败，Worker没有运行；不得记为Collator失败。

新增只读工具 `scripts/r60_common2_hf_cpu_image_probe.py` 是当前唯一立即推荐的诊断入口。它不提交Job，不修改Bucket，只输出SAFE聚合状态。**该工具编写完成不等于在Owner Mac真实执行完成；目前没有其真实回执。**

## 二、已证实的Real1000 / Common2数据里程碑

| 环节 | 有证据的当前状态 | 严格限制 |
|---|---|---|
| Real1000技术粗筛 | 1000条已冻结、跨285个故事，三消息源绑定通过 | 不是1000条文学质量PASS |
| Sample100/Pilot20 | 冻结100校准，20 Pilot完成多模型评审及分歧对照 | 多模型投票不构成真值 |
| Common2 | 独立盲审2条六维质量PASS，来源同原冻结池绑定 | 独立性为自述，不能升级为绝对ground truth |
| Supabase历史恢复 | 对2条恢复103和243条持久化历史，尾三消息完全匹配 | 不等于当年实际发送System/世界设定/Prompt |
| 私有实验SFT | 已生成2行11历史消息输入+冻结目标，`COMMON2_SFT_EXPERIMENTAL_2_READY__TRAIN_HOLD` | `SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT`，未伪造System |
| Mac真实Qwen tokenizer | 固定revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`，两条输入2552/4048 token，PASS | 不代表ms-swift Collator PASS |
| Mac `--stage both` | `COMMON2_CPU_TEMPLATE_AUDIT_HOLD` | Mac不装全套ms-swift/PyTorch，回到HF CPU |
| CPU2 stage+sync | 27文件、2条输入；`R60_COMMON2_HF_CPU2_REMOTE_READY_PASS`和`R60_COMMON2_SYNC_READY__NO_JOB` | 文件存在与完整性，不代表Job成功 |
| CPU2 Job | 原Job镜像参数Error；SDK镜像修复返回`SAFE_REMOTE_OR_RUNTIME_HOLD` | 无新Job ID、Worker有效运行证据尚未确立 |
| R50全量隔离 | 未完成（已知五个story无重叠仅部分验证） | 正式训练准入0，禁止GPU |
| Wave40 | 已从1000中确定性选40个新故事（20/16/4字数配额），Sample100故事重叠0 | 仅候选位置已准备，独立质量盲审暂停 |

**Key：** `r60-common2-cpu2-20261112T032815Z-71c840b37254`。HF Bucket前缀：
`hf://buckets/adradar/storyforge-training/preflight/r60/common2/cpu2/`。
Owner Mac只读源stage：
`$HOME/.local/share/storyforge/r60/hf-cpu2-stages/$RUN_KEY`。
私有两条实验数据：
`$HOME/.local/share/storyforge/r60/private/r60-real1000-common2-sft-experimental11-v1`。
Owner工作树 `$HOME/workspace/storyforge-r60-4router-review`（此前常为detached HEAD；`r60/p4-generation-eval-framework`可能被`storyforge-r60-ledger-diagnostics`另一工作树占用）。
代码目标分支 `r60/p4-generation-eval-framework`，PR #25 / 主线Issue #26。

## 三、接手P0：先只读复核，不创建任何Job

1. 先查最新目标分支`HEAD`与`git worktree list`、`git status -sb`。核对`AGENTS.md`、本文和`docs/R60_COMMON2_HF_CPU2_SYNC_SUBMIT_VERIFY_20261112_CN.md`，**不要因旧文档附录中的“立即submit”命令再次执行旧入口**。
2. 确认新工具存在，先`python3 -m pytest -q tests/test_r60_common2_hf_cpu_image_probe.py tests/test_r60_common2_hf_cpu_image_retry.py tests/test_r60_common2_hf_cpu_stage.py`；合成测试不等于真实Job。
3. Owner Mac以独立HF CLI venv执行只读probe（代码已在仓库，**没有必要下载Transformer、ms-swift或权重**）：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
HF_ENV="$HOME/.local/share/storyforge/venvs/hf-cli"
RUN_KEY="r60-common2-cpu2-20261112T032815Z-71c840b37254"
STAGE="$HOME/.local/share/storyforge/r60/hf-cpu2-stages/$RUN_KEY"
"$HF_ENV/bin/python" scripts/r60_common2_hf_cpu_image_probe.py \
  --run-key "$RUN_KEY" --stage "$STAGE" \
  --old-job 6af53990ab34849891aecb44
```

4. 先验证`local_stage`、`remote_ready`、`old_job`、`retry_marker`等SAFE字段。若`retry_marker=PRESENT`，标记只代表一次尝试，**不证明已创建Job**；必须在Owner Mac有权限的`hf jobs`端查看所有属于本次RUN_KEY的Job、其status和创建时间；ChatGPT HF连接器此前读Job返回403/404，不足以反证。
5. 若任一环节HOLD，保留原始内容、stage、Marker与旧Job；将失败归类为SDK接口、Job状态对象、Bucket权限/文件集、网络/认证、Worker容器参数或未知。**禁止用盲试/重复调用run_job排错。**

**P0交付：** 一份不含任何私有正文/ID映射的SAFE诊断回执；明确回答“是否存在第二个Job？是否有CPU Worker实际运行？失败发生在哪个阶段？” 严格注明证据不足处。

## 四、接手P1：证据允许时的修复顺序

- 如果已经存在新Job，直接只读查看状态/安全日志及`results/$RUN_KEY/R60_COMMON2_CPU2_SAFE_RECEIPT.json`，不得重复创建。只有出现`COMMON2_CPU_TOKENIZER_COLLATOR_PASS__R50_TRAIN_HOLD`且`cases=2`、`collator_verified=true`才算真实Collator成功。
- 如果没有新Job，且能可靠证明旧Job镜像错误、运行键/源哈希完整、Marker来源与未创建Job事实，**先修复SDK的Typed API兼容问题并新增测试/只读预检**，再按项目既有授权和防重复策略决定单次CPU-only执行。不能在未验证的API上盲删Marker后再次submit。
- 不要重新运行`scripts/r60_common2_hf_cpu_submit.sh submit`；原命令把`--name`解析成Docker镜像。现有SDK恢复入口`scripts/r60_common2_hf_cpu_image_retry.py`也已经真实HOLD，不能假设它可用。
- 对CPU Worker的镜像、Bucket `Volume`形态、HF SDK的`inspect_job`状态字段、PyTorch镜像依赖与`pip`冲突，优先做无私有输入的静态检查及mock回归。若需要修复Worker，记住远端已冻结Stage包含旧Worker：**只改GitHub不能自动修复已同步字节**；新代码必须以新的、经验证的独立运行工件发布，禁止原地覆盖。
- Owner已经要求删除“付费CPU逐Job单独确认及双环境变量门禁”的项目约定；按`AGENTS.md §2.1`行事。**这不等于允许重复创建Job，也不授权GPU/训练。**

## 五、接手P2：真实Collator与后续主线

1. 使用HF CPU上的固定`ms-swift==4.5.3`、`transformers==5.16.1`、Qwen同revision及冻结`scripts/hf_label_mask_audit.py`，验证**仅最后一条assistant目标参与Loss，历史全部mask**，长度/结束标记和实际Collator一致。Mac仅用标准库、HF CLI/SDK及轻量Tokenizer，不安装完整训练栈。
2. 保留`train_admitted=0`、`quality_v1_admitted=0`、`gpu_started=false`直至R50**完整**隔离、世界设定证据及Owner正式准入审核。不能用已知5个story的零重叠替代R50完整排除。
3. 两条链路打通之后，才恢复Wave40跨故事六维盲审，继续Real1000高质量数据扩展。不要因RolePlay 11月10日以后的普通消息较新而改变优先级；没有生产服务器权限，生产留证功能仍`DEFERRED_NO_PRODUCTION_ACCESS`。
4. 绝不向公开GitHub提交私有消息、真实源位置crosswalk、原始盲审文本、Bucket token、R50正文或模型权重。GitHub只放可复现脚本、测试、SAFE状态/文档；Owner私有路径下新文件0600、目录0700、create-only。

## 六、事故记录、状态规范和交付标准

事故及经验：`huggingface_hub 0.36.2`的Mac项目环境无`list_bucket_tree`，将其直接升级到2.4.0引起与`transformers 4.57.1`的依赖冲突；后改独立`~/.local/share/storyforge/venvs/hf-cli` 1.6.x，并为CLI补装`click`，Bucket同步成功。**不要在项目虚拟环境强装最新HF Hub。** Connector直接提交`403`与Owner Mac CLI授权能力不同。第一次CLI镜像参数错误不是样本问题。第二次SDK修复综合HOLD尚不知具体阶段，优先只读probe。

每阶段输出四类状态并有依据：`DONE_WITH_RECEIPT`、`BLOCKED_WITH_REASON`、`NOT_ATTEMPTED`、`UNKNOWN_NEEDS_READ_ONLY_CHECK`。不得把计划、CI合成PASS、调用尝试、Bucket文件存在推断成真实CPU Worker成功。

交接完成标准：新Agent能够依据本文件与当前GitHub，自行给出只读核验命令、复核版本和证据；知道不能直接重复提交；下一步技术验收与R50隔离清晰。**本轮仅交接，不执行新HF Job，不修改冻结样本。**
