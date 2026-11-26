# StoryForge R57 G2 — 目标哈希锚定的世界 UUID 只读回放（Owner Mac）

**状态：** `EXACT_TARGET_LINEAGE_OWNER_PASS__TARGET_ANCHORED_WORLD_UUID_AUDIT_PREPARED__SEMANTIC_ALIAS_HOLD`。

2026-10-26 Owner Mac 八组 JSONL 原始字节检查和历史 14/9/8 回放均 PASS；R46 Train49、Val15，R54 Train31、Val9 的每条最终 Assistant 目标哈希均在冻结 Gold195 中找到唯一精确记录。Gold195 自身有 195 个互不相同的目标 SHA。故可将 Trainer 末轮目标 SHA256 作为**精确连接键**，引用匹配 Gold 行的 `story_id` 或 `source_story_id`，恢复历史 Trainer 记录对应的**原始世界 UUID**；不需要从匿名故事文本中猜测故事身份，也不应编造丢失的 Trainer `metadata`。

新增 `scripts/r57_g2_target_anchored_world_audit.py` 完全只读：限定八个固定来源路径，逐一核验四个 Git Blob 完整字节以及 R46/R54 四个 compiled Trainer SHA256；要求完整八组、195 个唯一 Gold 目标、历史 14/9/8、5 条 role/content 完整消息及历史精确重复；全部历史 R46/R54 Trainer 行都要**唯一**命中 Gold195，否则 HOLD。

输出不含原文、逐条 SHA、真实世界 UUID 或文件路径，仅有以下安全计数：

- 八组各自的不同故事 UUID 数量。
- 28 组两两来源 UUID 交叉数、两侧落在交叉故事中的行数。
- v0.1 / R46 / R54 三次 SFT 内部 Train ↔ Val 的同 UUID 世界重叠数。
- 按 Gold87/Gold108 和历史目标 Train-only / Val-only / Both / 无精确目标匹配四类别，统计**同历史 Train/Val 世界 UUID**的行数。特别关注 114 条“没有目标精确匹配”的候选中有多少仍处于已经用于训练的故事 UUID。
- 准入标记永远为零；世界别名分量、跨 UUID 角色同一性、近似语义重复、ms-swift 监督模板仍待独立审查，不因此工具 PASS 而转 PASS。

## 执行（Mac，使用已经找到并复制的私有 R46/R54 原始文件）

在本机既有 StoryForge 仓库根目录：

```zsh
git status --short
git fetch origin r57/v03b-data-design
git switch r57/v03b-data-design
git pull --ff-only origin r57/v03b-data-design

PRIVATE="$HOME/.local/share/storyforge/r57/private"
python3 scripts/r57_g2_mac_preflight.py \
  --repo-root "$PWD" --private-root "$PRIVATE"

python3 scripts/r57_g2_target_anchored_world_audit.py \
  --repo-root "$PWD" --private-root "$PRIVATE"
```

**前一命令必须返回全部 8 组 `BYTE_PIN_PASS`；否则停止。** 后一命令只打印脱敏聚合 JSON，不写任何文件、不读取 R50。可以把后者的完整 JSON（人工确认）提供给 Owner 协调者；严禁粘贴私有 Trainer 原文、逐条 SHA/世界 UUID 或任何 R50 内容。

## 结论的证据层级

- `source_byte_pins_verified_by_cli=true`：表示本机程序对既存文件重新核对冻结字节身份，而非 GitHub Actions 或 HF 服务端自动重新核验 Owner Mac。
- `compiled_trainer_rows_uniquely_mapped_to_gold195`：只能证明 R46/R54 最终 Assistant **目标文本的唯一匹配**，由 Gold 原始元数据取回世界 UUID。不会证明编译后 Trainer 的前置历史与 Gold 原始行相同。
- `within_run_train_val_uuid_overlap`：只反映**逐字相同的故事 UUID**，不是跨世界角色/笔名/别名图；若出现非零应在未来的数据拆分前进行额外隔离审查；为零也**不是**世界独立 PASS。
- Gold195 `NO_EXACT_TARGET_IN_PRIOR_SFT = 114` 仅表示最终回复目标未被那三次 SFT 逐字重复使用。即使其 UUID 未命中历史 SFT，仍不能认定是新的 Held-out 或有资格进入 Dataset v0.4。

## 下一个门禁

在 Owner Mac 复核各世界 UUID 与别名/角色连通图，补充有签核证据的 target-time 故事卡、同意/年龄、审核范围、版权和质量；之后才做双 Reviewer 逐条审阅。Dataset v0.4 仍为 0 条准入。R55 四项 HOLD 保持，R50 不访问，GPU/HF 付费作业禁止。
