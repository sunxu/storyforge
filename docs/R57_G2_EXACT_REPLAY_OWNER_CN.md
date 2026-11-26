# StoryForge R57 G2 — 冻结 Trainer 字节级来源检查与精确交叉审计

**版本：** v1，`2026-10-26`。**状态：** `FOUR_GIT_SOURCE_BYTE_REPLAY_PASS__FOUR_PRIVATE_TRAINER_SOURCES_PENDING__ALIAS_HOLD`。

## 为什么新增这条审计路径

历史 `scripts/prepare_sft.py` 生成的实际 Trainer JSONL 可以只剩 `{"messages": [...]}`，不含 `metadata.story_id`。此前的 `r57_source_index_export.py` 要求元数据与别名图，对这种文件会报 HOLD，即便其原始 SHA256 完全正确。

因此本工具 `scripts/r57_trainer_exact_replay.py` 先**按实际 Trainer 文件原始字节和已归档源 pin 进行精确交叉**，不需要伪造 story_id，不生成假的 alias token：

1. 固定 8 组白名单：Gold87、Gold108、v0.1 Train65/Val15、R46 Train49/Val15、R54 Train31/Val9。
2. 对 Git 仓库前 4 组验证冻结 Git Blob SHA-1（基于完整文件字节重算）；对私有 Trainer 后 4 组核对已归档 **compiled Trainer SHA256**。
3. 从实际最后一条 Assistant `content` 计算 UTF-8 SHA256，与存在的原元数据目标哈希逐条对照；输出只含集合计数，不写出任何逐条哈希或剧情。
4. 独立比较目标 SHA256、全消息 role/content 投影和目标之前历史 role/content 投影。注意：投影并非 ms-swift 原始输入字节或 loss/token 模板一致性证明。
5. 完整八源时重放 R54 Train31 对 R46 Train49 / Val15 的 **14 / 9 / 8**；若不匹配直接 HOLD。
6. **真实故事/别名连通图、Train/Val world isolation、语义近重复、逐条授权与审核始终单独 HOLD**，不从“target 0 交叉”推导世界独立。

## 只读核对四组公开于 Git 仓库的源

```bash
git switch r57/v03b-data-design
python3 -m unittest discover -s tests -p 'test_r57_*.py' -v

# 无需 R46/R54 私有文件；不扫描 R50、不下载模型、不启动任务
python3 scripts/r57_trainer_exact_replay.py \
  --repo-root "$PWD" --mode draft
```

只有将近实际 Git checkout 的四组冻结字节完全匹配，才会显示 `original_file_byte_pins_checked_by_cli: true`。此前 CI 已自动重放真实四组并断言源 87/108/65/15、Gold195 不重复、六个集合对 exact target/input/history 均为 0、Gold195 digest 全量复算、真实数据准入 0。

Gold108 必须严格识别**三种**实际原始元数据格式：**90** 行 `story_id + target_sha256`，**15** 行 `story_id + target_sha256_utf8`，**3** 行 `source_story_id + target_content_sha256`。2026-10-26 的第一版 105/3 统计**已更正**；严格合成测试与真实字节 CI 会拒绝偏离 90/15/3 的源。

## 完整八源：仅 Owner 在私有 Mac 环境运行

仅在四份**实际编译后 Trainer JSONL**的来源与冻结 SHA256 独立核对成功时可执行，不需要给 ChatGPT 上传或给 GitHub 提交 Trainer 原文：

```bash
PRIVATE="$HOME/.local/share/storyforge/r57/private"
python3 scripts/r57_trainer_exact_replay.py \
  --repo-root "$PWD" --private-root "$PRIVATE" --mode full \
  --source GOLD87 --source GOLD108 \
  --source V01_TRAIN --source V01_VALIDATION \
  --source R46_TRAIN --source R46_VALIDATION \
  --source R54_TRAIN --source R54_VALIDATION \
  --safe-out "$PRIVATE/R57_G2_EIGHT_SOURCE_EXACT_SAFE_01.json"
```

工具不自动新建目录；安全回执输出只能创建新文件（0600，`O_EXCL`，拒绝符号链接目标），拒绝覆盖。所有源路径为代码固定白名单，不联网、不训练。**不要将存储在 `PRIVATE` 的原始 Trainer 文件、来源索引、世界别名图、逐条哈希提交 Git**。检查后，安全汇总 JSON 只在完成隐私审核后归档。

与 `r57_source_index_export.py` 的关系：两者互不替代。**字节/target 精确重复**可能 PASS，但 `source_index_export.py` 仍因没有单独可信的世界来源映射而 HOLD。下一门禁需要 Owner 用已校验的 frozen source→compiled Trainer 行对齐证据，把 `source_story_id`/alias component 关联回来，不能因为数据没有 metadata 就认为 40 条完全独立。

**边界：** R50 不得访问；R55 79/69/4 冻结判断及 4 HOLD 不改判；Dataset v0.4 仍为零条准入；本阶段绝不执行 HF Job、GPU、训练、自动晋升或 PR merge。
