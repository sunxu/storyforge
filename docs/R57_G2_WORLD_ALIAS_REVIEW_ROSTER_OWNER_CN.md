# R57 G2 世界 / 角色别名审核：Owner 私有证据清单

**版本：** 2026-10-26。**门禁：** `EIGHT_SOURCE_TARGET_ANCHORED_UUID_OWNER_PASS__ALIAS_SEMANTIC_REVIEW_NOT_STARTED__NO_ADMISSION`。

Owner Mac 已提供 8 个真实字节 pin 的 UUID 匹配计数，R46/R54 compiled Trainer 104 行目标均唯一对应 Gold195，历史 R54→R46 14/9/8 重放 PASS，跨角色和故事别名语义仍 HOLD。

根据已经返回的计数，Gold195 中 114 条没有旧 SFT 的最终回复逐字目标匹配，其中 82 条与至少一条历史 SFT 共享**故事 UUID**，剩余 32 条位于 Gold87 的两个历史未用 UUID 故事里，分别 **14 + 18**。这些 32 条不是独立 Held-out，也不是自动可用训练样本；`R55` 曾出现的开发题、世界同一性、故事目标时点卡、权利、人物同意及安全仍未审核。

## 新工具：从八份冻结源生成本机私有世界 UUID 审查清单

`scripts/r57_g2_owner_world_review_roster.py` 读取代码严格白名单 8 份 JSONL，分别重算完整 Git Blob SHA-1 与 R46/R54 compiled Trainer SHA256；重放 14/9/8 与 5 条完整消息重复；依 Gold195 唯一最终目标哈希恢复 104 个 Trainer 样本的原始故事 UUID；只输出安全计数。可选地在本机私有目录创建清单，**不扫描 R50、无网络、不运行模型或训练**。

清单每个 UUID 的私有字段包括：`source_story_uuid_PRIVATE`、该 UUID 在八组原始源的行数、其中尚无旧 SFT 精确目标重复的 Gold 数量、是否在旧 SFT 被使用；**所有** `owner_declared_component_token_PRIVATE` 默认为 `null`，`owner_alias_semantic_review_status` 默认为 `PENDING_NOT_VERIFIED`，`dataset_v04_decision` 永远为 `HOLD_NOT_REVIEWED`。不会从故事 UUID 或名称自动推断角色别名。

八源预计存在 29 个不同故事 UUID：Gold87 5 + Gold108 8 + v0.1 Train15 + v0.1 Val2 − 一个 Gold87↔v0.1 Train 的 UUID 交集。该计数在实际 Mac 只读重放前仅为源计数推导。

## A. 无写入核验，Mac 终端

```zsh
# 在已有 StoryForge 仓库根目录
git status --short
git fetch origin r57/v03b-data-design
git switch r57/v03b-data-design
git pull --ff-only origin r57/v03b-data-design

PRIVATE="$HOME/.local/share/storyforge/r57/private"

python3 scripts/r57_g2_mac_preflight.py \
  --repo-root "$PWD" --private-root "$PRIVATE"

python3 scripts/r57_g2_owner_world_review_roster.py \
  --repo-root "$PWD" --private-root "$PRIVATE"
```

若 preflight 不再显示 8/8 `BYTE_PIN_PASS`，停止。后一命令**只读无写入**；预计输出 `world_uuid_count=29`、`gold_world_uuids_without_historical_sft_uuid=2`、`gold_rows_without_target_and_world_uuid_exact_match=32`、`v04_admitted=0`。

## B. 可选：实际创建本机私有审核清单

```zsh
umask 077
python3 scripts/r57_g2_owner_world_review_roster.py \
  --repo-root "$PWD" --private-root "$PRIVATE" \
  --private-roster-name "R57_G2_WORLD_ALIAS_REVIEW_$(date +%Y%m%d_%H%M%S)_PRIVATE.json"
```

生成的文件包含原始故事 UUID 和跨八源分组行数，保存在 `$PRIVATE`，仅本机持有；目录应在 Git 仓库之外。文件创建权限 `0600`，拒绝覆盖既有文件及符号链接目标。**绝对不要上传这份 PRIVATE JSON、原始故事正文、真实 UUID 或逐条目标 SHA**。终端打印的安全统计可以发给 ChatGPT。

## C. Owner 后续需补证的世界组件判定

针对 29 个私有 UUID，结合**源故事、人物表、角色别名跨故事引用和目标时点规则**给出有来源证据的语义同一性/独立性判定；不同 UUID 可能属于同一个世界，名字相同也未必是同一人。没有证据的组件关联必须 HOLD，不能由程序默认为不同。Owner 自审完成后再由独立审阅者复核，并明确审批边界。

不能因为 32 条位于历史没有用过的故事 UUID 就自动把它们设为独立 Held-out：Gold195 已是开发候选池，需同时排除 R55 旧开发题及其他已看过的评估题。已有训练世界里的新增 Gold 回复（82 条）也不是自动禁用训练，是否允许用于**后续训练**与是否能当作**独立评估**是两个不同的问题。

全程保留 Dataset v0.4 正式准入 0，R55 四项 HOLD 不改判，R50 不访问，GPU/HF 付费任务不运行。
