# StoryForge R58：132 条 Assistant-first 历史输入诊断（B 路线）

## 为什么不是直接切掉开头 Assistant

冻结 Gold195 中的 132 条历史以 Assistant 消息开头。这可能只是截断时保留了此前的模型回复，也可能包含第一次出现的角色称谓、地点、世界状态或剧情前提。直接移除首条 Assistant 可以让剩余历史在**角色形状上**成为 User-first，但不保证事实/文学连续性。因此这种操作只能形成**待审建议视图**，不能自动准入训练或把移除视作来源事实。

本轮是离线结构诊断，不延长 Grok 网页授权，也不访问 HF/GPU。不会把任何虚构 User 消息补到历史前面，不重新写任何冻结 Gold。

## Mac 本机操作（数据已迁移至 ~/.local/share/storyforge/r58）

在 Git 分支 `r58/roleplay-sft-skill-v01` 仓库根目录：

~~~bash
git pull --ff-only

R58_PRIVATE="$HOME/.local/share/storyforge/r58"

python3 -m unittest discover -s experiments/r58_quality -p 'test_gold195_assistant_first_diagnostic.py' -v

# 第一次运行：仅校验结构，终端只有 SAFE 计数。
python3 experiments/r58_quality/gold195_assistant_first_diagnostic.py \
  --repo-root "$PWD" \
  --private-card-gold-review "$R58_PRIVATE/gold195-card-gold-review-v1.jsonl"

# 第二次运行（可选）：生成 132 条私有对照审核包，仅用于逐案人工/AI 核查。
python3 experiments/r58_quality/gold195_assistant_first_diagnostic.py \
  --repo-root "$PWD" \
  --private-card-gold-review "$R58_PRIVATE/gold195-card-gold-review-v1.jsonl" \
  --private-comparison-output "$R58_PRIVATE/gold195-assistant-first-comparisons-v1.jsonl"
~~~

目标新文件必须不存在；私人源文件权限 `0600`，R58 目录权限 `0700`，输出 `0600`。不要把原始私人 JSONL、世界卡、故事正文或真实 case ID 上传 GitHub、公共 CI 或聊天。

## 审核包与结论边界

每条审核包保留：原始 `original_history`、去首条后的 `proposed_history_if_first_assistant_removed`、待回复 User、完整 Gold 目标、世界卡快照、源哈希与拟议历史哈希。由审阅者判断开头 Assistant 是否携带不可丢弃的事实、是否已由后文补足、移除是否破坏关系/剧情/禁令和离线卡片是否足以补充。

所有审核标记均为 UNREVIEWED；`training_candidate_messages=null`、`approved_history_transform=false`、`quality_v1_admitted=false`。初期 132 条全部 HOLD，**即使角色形状都符合交替排列也不代表 132 条可训练**。将来若删除开头回复或缩短窗口，须另有独立语义确认、卡片认证、token/last_round mask 验证、世界组件隔离，再由 Owner 决定训练资格。

出于可追踪性，建议后续对比“保留完整 Assistant-first 历史（若训练栈支持并已验证）”、“剔除开头孤立 Assistant（仅经人工/AI 审查认定可丢）”与“样本继续 HOLD”三种方式。任何训练栈兼容性均需要实际 CPU tokenizer/collator 证明，而不是猜测。

## 验收标准

成功时 SAFE 回执 `ASSISTANT_FIRST_132_SHAPE_DIAGNOSED__SEMANTIC_HOLD`，预期 `source_rows_checked=195`、`assistant_first_hold=132`、`user_first_unchanged=63`。如哈希、历史角色或源格式异常，则直接 HOLD，不能悄悄丢行或制造新的输入记录。R50 永久封存，GPU 不自动启动。
