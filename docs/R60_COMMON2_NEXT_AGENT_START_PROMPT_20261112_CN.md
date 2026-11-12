# StoryForge R60 — 下一Agent启动提示词（复制使用）

> **2026-11-12 最新权威覆盖声明：Common2 CPU技术验收已PASS（优先于以下全部旧“IMAGE_FIX_HOLD/Collator未知”段落）。** 第五轮真实HF Job `6af570089737d9a9e093d501` 已 `COMPLETED`，Worker输出 `R60_CPU2_V2_REAL_COLLATOR_PASS__R50_TRAIN_HOLD`；已验证两条实验输入的Tokenizer、严格R18 Label Mask、实际ms-swift Collator。**不再执行下文任何旧Submit、重试、Stage重建命令**。当下只读验签既有SAFE回执、分析原生/Swift模板不等价、核验完整R50排除、形成Owner训练准入决策；`SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT`、`native_template_token_parity_verified=false`、`r50_complete_exclusion_verified=false`、`train_admitted=0`、GPU/SFT HOLD。环境和可复用命令详见 [HF Jobs Mac CLI CPU2实战手册](standards/HF_JOBS_MAC_CLI_CPU2_PLAYBOOK_20261112_CN.md)。本覆盖声明只更新Common2，不替代其他Agent并行状态。\n\n
你现在接手 `sunxu/storyforge` 的R60 Real1000 Common2 SFT CPU验收主线，**当前任务是先确认既有HF CPU2镜像修复尝试的真实状态，而不是直接启动新Job**。

请首先完整阅读：
- `AGENTS.md`
- `docs/R60_COMMON2_NEXT_AGENT_HANDOFF_20261112_CN.md`（**当前权威交接任务书**）
- `docs/R60_COMMON2_HF_CPU2_SYNC_SUBMIT_VERIFY_20261112_CN.md`
- `docs/R60_COMMON2_SFT_FIRST_END_TO_END_20261112_CN.md`
- `docs/R60_REAL1000_QUALITY_FIRST_DECISION_20261112_CN.md`

GitHub仓库 `sunxu/storyforge`，目标分支 `r60/p4-generation-eval-framework`，PR #25，主线Issue #26。以当前远程HEAD与Owner SAFE回执为准，先核验分支和工作树，不覆盖并行Agent的任何工作。Owner Mac只读工作树 `$HOME/workspace/storyforge-r60-4router-review` 可能是detached HEAD；分支可能占用于 `$HOME/workspace/storyforge-r60-ledger-diagnostics`。避免强制切换已占用的分支。

**最新已知事实：**

1. 冻结Real1000里Common2两条独立六维质量PASS，历史103/243条已恢复；两条实验性11消息SFT输入已生成、`SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT`，不伪造System或世界卡；Mac固定Qwen Tokenizer真实计数2552/4048 PASS。
2. HF CPU2私有数据stage 27文件及Bucket READY均PASS。RUN_KEY `r60-common2-cpu2-20261112T032815Z-71c840b37254`，stage `$HOME/.local/share/storyforge/r60/hf-cpu2-stages/$RUN_KEY`，HF Bucket `hf://buckets/adradar/storyforge-training/preflight/r60/common2/cpu2/`。
3. 首次HF CLI Job ID `6af53990ab34849891aecb44` 为镜像规格解析Error `docker.io/--name`，Worker未执行。其后SDK镜像修复脚本真实Owner回执 **`R60_COMMON2_CPU2_IMAGE_FIX_HOLD` / `SAFE_REMOTE_OR_RUNTIME_HOLD`**。该错误不能确认新Job是否创建。新的 `scripts/r60_common2_hf_cpu_image_probe.py` 仅只读，**尚无Owner实际probe回执**。
4. 你**不得重试提交、删除本地重试Marker、重传/覆盖Stage或启动GPU/训练**。不能把GitHub合成测试PASS当成真实Collator通过。HF连接器对Job曾返回403/404，Owner Mac HF CLI权限较完整。优先采用Mac只读probe+Job列表。
5. Wave40已从冻结1000条中准备40条跨故事候选，与Sample100故事不重叠，**盲审暂停**；两条Common2 SFT技术验收优先，完整R50排除未完成，训练准入0。RolePlay生产留证不在当前关键路径。

**按以下顺序执行交接后的工作：**

P0：读取远程现状及`scripts/r60_common2_hf_cpu_image_probe.py` / 测试，核对旧Job、远程READY、本地源SHA256、`retry_marker`以及是否存在第二个Job。首先只读，产出分阶段SAFE回执，精确区分“真实已发生”“推测”和“未知”。优先验证实际HF SDK `inspect_job` 返回结构与现有校验器是否匹配。不得由于SDK统一错误码就推断状态。

P1：只有证据证明不存在已提交/运行中的第二Job，且原Marker与代码、运行记录充分核对后，才评估修复`HfApi.run_job`兼容性。先小型离线合成测试，保留独立运行键的唯一性和不覆盖证据。用户已取消重复的CPU付费授权变量门禁，但这不表示允许自动批量重试或训练。

P2：一旦真实HF CPU Worker返回两条样本Collator及final-assistant-only loss mask PASS，继续R50完整隔离、技术数据准入、源上下文合理性复核；结果未齐时保持`train_admitted=0`和GPU禁启。最后再恢复Wave40质量盲审，不要优先重采11月10日后的普通数据。

**明确交付：** 一份中文简洁状态表（工作项、真实证据、判定、剩余障碍），可复制的Owner Mac最小只读命令，针对明确故障的可复用修复（若需要，附测试与CI），任务书/Issue #26更新及下一执行者提示词。禁止泄露私有故事文本、客户ID、凭据、模型权重及R50正文。除非Owner明确从交接工作切换到执行阶段，否则本次先核验并准备方案，不提交HF Job。

从P0只读审计开始，不要先询问已经提供的RUN_KEY、Job ID或工作目录。
