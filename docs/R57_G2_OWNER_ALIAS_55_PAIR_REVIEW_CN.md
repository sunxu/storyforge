# StoryForge R57 — G2 跨故事语义别名证据复核（Owner Mac）

**状态：** `G2_EIGHT_SOURCE_EXACT_TARGET_AND_UUID_OWNER_PASS__SEMANTIC_ALIAS_NOT_VERIFIED__NO_ADMISSION`。

2026-10-26 Owner 两次回传完全一致：29 个冻结来源 UUID（27 个历史 SFT 世界 UUID，2 个在历史 SFT 中未发现**相同 UUID**的 Gold 故事），Gold195 中 114 条目标无历史 SFT 精确重复，其中 82 条仍与已用历史 SFT 共享世界 UUID，仅 32 条位于另外 2 个 UUID 的故事（14 + 18）。**这不是新独立测试集，也不是训练准入。**

别名门禁不允许从“不同 UUID”推导“不同世界”。必须在 Owner 本机阅读原始故事、角色设定和历史版本证据，判断：两个候选 Gold 故事与 27 个历史 SFT 故事的身份／世界／角色关系，以及两个候选故事之间的关系。该流程总计 2×27+1 = **55 条需要逐项明确处理的对照**。不支持自动归并或自动填“无关联”。

## 1. 生成 Owner 私有空白审查问题（Mac）

在已存在的 StoryForge 仓库根目录运行，代码分支 `r57/v03b-data-design`：

```zsh
git status --short
git fetch origin r57/v03b-data-design
git switch r57/v03b-data-design
git pull --ff-only origin r57/v03b-data-design

PRIVATE="$HOME/.local/share/storyforge/r57/private"
umask 077

python3 scripts/r57_g2_mac_preflight.py \
  --repo-root "$PWD" --private-root "$PRIVATE"

REVIEW_NAME="R57_G2_ALIAS_EDGE_REVIEW_$(date +%Y%m%d_%H%M%S)_PRIVATE.json"

python3 scripts/r57_g2_alias_pair_review.py \
  --repo-root "$PWD" --private-root "$PRIVATE" \
  --create-private-name "$REVIEW_NAME"

echo "本机私有清单已准备：$PRIVATE/$REVIEW_NAME"
```

只有八份固定源原始字节与历史 SHA256/Git Blob pin 全部一致时才允许生成。程序会重跑 14/9/8、五条 role/content 完全重复、104 条编译后 Trainer 目标唯一关联与 29 世界清单。仅本机在 `$PRIVATE` **新建**模式写入一份 0600 权限 JSON，拒绝覆盖已有文件或符号链接；终端输出只有安全计数，不包含 UUID。

## 2. 由 Owner 根据原始证据手工填写

使用本机编辑器在 `$PRIVATE/$REVIEW_NAME` 打开 JSON。该文件内的 `questions_PRIVATE` 每一项包含：两个真实故事 UUID（必须保持不变）、比较类别，以及三个仅允许人工填写的字段：

- `owner_decision`：`UNREVIEWED`（默认）、`LINKED_WITH_EVIDENCE`、`DISTINCT_WITH_EVIDENCE`、`HOLD_INSUFFICIENT_EVIDENCE`。
- `evidence_reference_PRIVATE`：仅填写 Owner 本地证据档案标识，不填写 R50 路径或内容。只要有人工结论（含 HOLD），就必须填写非空引用。
- `owner_notes_PRIVATE`：可选的本机私有说明（不进入 GitHub），记录哪些故事卡版本、角色表、原作者声明或已给上下文支持判断。

**不要修改**任何两个 UUID、`comparison_kind`、55 条对照集合、`schema`、`all_world_independence_certified=false`、`dataset_v04_admitted=0`、`training_authorized=false`。不要猜测关系；证据不足必须使用 `HOLD_INSUFFICIENT_EVIDENCE`，不可自动写 `DISTINCT_WITH_EVIDENCE`。

如果你只想知道 2 个待查世界在历史中出现在哪里，可以在本地打开上一步建立的 `R57_G2_WORLD_ALIAS_REVIEW_*_PRIVATE.json`，查找 `same_exact_uuid_seen_in_previous_sft=false` 且 `gold_final_targets_without_previous_exact_match>0` 的两行；不要把真实 UUID 或私有故事原文发到聊天。

## 3. 验证私有人工填写结果（不写文件）

```zsh
python3 scripts/r57_g2_alias_pair_review.py \
  --repo-root "$PWD" --private-root "$PRIVATE" \
  --audit-private-name "$REVIEW_NAME"
```

程序将重新验证八份来源 pin，要求 **55/55** 对照集合不增不减、UUID 不变、所有决议值合法、对每条实际填过的判断必须提供来源引用；任何意外改动直接 HOLD。它只打印 `UNREVIEWED`、`LINKED_WITH_EVIDENCE`、`DISTINCT_WITH_EVIDENCE`、`HOLD_INSUFFICIENT_EVIDENCE` 的数量。

**即使 55 项全部填写，这仍是 Owner 人工工作覆盖率核验，绝不自动认证世界独立。** 真实别名图需由 Owner 汇总并独立复核正/负证据后才可更改 G2 世界隔离状态。逐条数据安全、年龄/同意、权利/质量与实验暴露则仍须单独门禁。

## 4. 只可分享安全输出

请仅返回第三步终端打印的脱敏计数 JSON。**禁止上传** `$PRIVATE` 下 55 对照原始 JSON、真实 UUID、目标 SHA 列表、角色/故事全文、R50 数据。R55 四项 HOLD 维持不变；Dataset v0.4 **0 条准入**；绝不启动 HF/GPU/训练/模型晋升。
