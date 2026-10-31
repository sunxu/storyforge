# R58 G1 — 已存在 HF 优先 Job 元数据回执的只读复核（SAFE）

日期：2026-10-31。适用情形：此前尝试运行 \`inspect_hf_priority_job_metadata.py\`，终端提示 \`HOLD: metadata receipt already exists; no overwrite\`。

**这只表示安全的独占写入拒绝覆盖，不能推出此前任务成功或失败。禁止删除、覆盖、改名、重算或将私有文件上传到聊天/GitHub。**

## 新增的只读入口

\`skills/storyforge-roleplay-sft/v02/r58_existing_priority_receipt.py\` 不调用 HF、Supabase、数据库、Trainer、Job 日志，也不创建输出文件。它仅从已有 Owner 私有 \`0700\` 根目录读取两个已有的 \`0600\` JSON：

1. \`g1_hf_gpu_signal_priority_one_private.json\`：前次已验证的单个潜在 GPU 日志信号 Job 优先账本。
2. \`g1_hf_priority_provider_metadata_private.json\`：已存在的提供商元数据回执。它可能来自先前有效执行，也可能是旧/不一致回执，因此必须独立交叉核验。

仅接受两个固定的 PRIVATE schema，且精确检验：规范 Job ID（**不打印**）、先前日志摘要（**不打印**）、CANCELED 状态、\`TRAINING_LOSS_GRAD_TELEMETRY\` 迹象、无参数更新结论、无输入 SHA256 证明、禁止扩样与 G1 HOLD。任何不匹配、缺文件、路径穿越、symlink、权限过宽或附加未知字段均拒绝并退出 42。复用 Skill v0.2 已验证的 \`O_NOFOLLOW\` + dirfd 安全私有读取代码。

## Mac 操作：不写私有文件

\`\`\`bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only

python3 -m unittest discover \
  -s skills/storyforge-roleplay-sft/v02 -p 'test_*.py' -q
ruff check skills/storyforge-roleplay-sft/v02/ --statistics

ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
python3 skills/storyforge-roleplay-sft/v02/r58_existing_priority_receipt.py \
  --private-priority-ledger "$ROOT/g1_hf_gpu_signal_priority_one_private.json" \
  --existing-private-metadata "$ROOT/g1_hf_priority_provider_metadata_private.json"
\`\`\`

本轮在隔离环境完成新增模块的 **14/14** 项合成测试；此前 Owner Mac 为 v0.2 **47/47 PASS + Ruff PASS**。因此最新集成目录的预期总量 **61 项**，以新 HEAD 的 Owner 本机输出为准。不得用此前 47 PASS 冒充最新 61 PASS。

## 输出解释

成功核对时返回 JSON 状态：

\`EXISTING_PRIORITY_METADATA_CROSSLINK_VERIFIED__PARAMETER_AND_INPUT_HOLD\`

其中 \`job_id_and_log_sha_match_private_priority=true\` 仅表示**两个现存 PRIVATE 账本中的字段相互一致**，不能证明 HF 服务端记录是真实且历史不可变、存在 optimizer step，或曾使用哪个训练来源。即使记录 \`command_intent_class=POTENTIAL_TRAINING_COMMAND_INTENT\`，也不能确认训练发生。

失败时只打印固定 HOLD 错误、不泄漏私有路径；**不要因此重新抓取历史日志或强制覆盖回执**。可在 Owner 机器本地调查权限、版本和来源绑定。

用户只需将命令打印的 SAFE JSON 和合成测试/Ruff 摘要贴到聊天；**绝不粘贴原 PRIVATE JSON、24 位 Job ID、日志 SHA、命令行或 R50 内容。**

项目状态不变：\`G1=HOLD\`、\`G2=HOLD\`、Train/Validation/Teacher 准入 0、最多固定五世界/20 回复、PR #7 Draft、不启动任何新 HF Job、不训练、不扩样。
