# R57 G3 — Owner Mac：Gold195 逐条历史精确曝光标签（私有）

**状态：** `G2_OWNER_EIGHT_BYTE_PINS_AND_14_9_8_REPORTED_PASS__G3_PRIVATE_TARGET_EXPOSURE_PREP__WORLD_ALIAS_HOLD__NO_ADMISSION`。

八源回放安全计数由 Owner 2026-10-26 本地命令提供：历史 Train 精确匹配 66、Validation 精确匹配 24、同时命中 9；去重后 81 个 Gold 目标曾出现于历史训练/验证，另外 114 个没有在这些数据集中找到**相同最终 Assistant 目标字节**。完整证据分组在 `docs/evidence/R57_G2_EIGHT_SOURCE_OWNER_EXACT_REPLAY_SAFE_20261026.json`，证据级别是 Owner 回传的本地核验结果，**不是新获得的 HF 提供商独立证明**。

## 为什么需要新的私有标注

之前的安全回执只能告诉我们 81 / 114，不能可靠地告诉 Owner 具体哪 114 条目标在历史 SFT 中没有精确重复。不能因此直接从 Gold195 任意抽题，更不能以“目标不一样”为由认定世界、历史、同义改写或 R55 20 条开发题无泄漏。

新增 `scripts/r57_g3_private_exposure_ledger.py`：直接只读前 4 组 Git Blob 和 Owner 已提供的 R46/R54 4 份 compiled Trainer 原始字节，重算固定 SHA256；确认 14/9/8 和 5 条完整消息精确重复；仅在 Owner 本机私有目录创建**195 行逐条映射**。每行包括来源池+序号、目标 SHA256、来源世界 UUID、与历史 Train/Val 的精确重叠类别、碰撞的历史 split 名、同 v0.1 的故事 UUID 标签，以及两类 **`HOLD_NOT_REVIEWED`** 门禁。它**不读取、不引用** R50，不检查模型输出，不决定训练准入。

Gold87：Train-only20 / Val-only0 / Both0 / 无精确目标匹配67。
Gold108：Train-only37 / Val-only15 / Both9 / 无精确目标匹配47。
合计：Train-only57 / Val-only15 / Both9 / 无精确目标匹配114。

## A. 无写入模式（推荐先跑）

```zsh
cd "$HOME/workspace/storyforge-r55-tooling" || exit 1
git status --short
git fetch origin r57/v03b-data-design
git switch r57/v03b-data-design
git pull --ff-only origin r57/v03b-data-design

PRIVATE="$HOME/.local/share/storyforge/r57/private"
python3 scripts/r57_g2_mac_preflight.py --repo-root "$PWD" --private-root "$PRIVATE"
python3 scripts/r57_g3_private_exposure_ledger.py --repo-root "$PWD" --private-root "$PRIVATE"
```

前一命令必须显示 8/8 `BYTE_PIN_PASS`。后一命令只在终端显示安全汇总，**无文件写入**；若 14/9/8、五条完整重复、81/114 或逐条来源意外不匹配，返回退出码 2 / HOLD。

## B. 可选：创建逐条私有检查表（绝不上传）

```zsh
umask 077
python3 scripts/r57_g3_private_exposure_ledger.py \
  --repo-root "$PWD" --private-root "$PRIVATE" \
  --private-ledger-name "R57_G3_EXACT_TARGET_EXPOSURE_$(date +%Y%m%d_%H%M%S)_PRIVATE.json"
```

该文件包含目标哈希与实际故事 UUID，**属于 PRIVATE**。仅在 `$PRIVATE` 目录新建，权限 0600，拒绝覆盖既有文件及符号链接目标；请勿上传、粘贴到聊天、发布到 GitHub、加入 Git LFS 或与陌生人分享。终端输出的安全计数可以经人工确认后返回给协调者。

## C. 下一个真正的 G2/G3 门禁

- **世界别名图 / 角色链接：** 原始 Trainer JSONL 未携带 source story UUID，因此现阶段只能重放 target、历史、role/content 精确关系。需通过先前冻结的源→编译后输入对齐记录，复核本机 Owner 审批过的世界组件图；不能用世界 UUID 不同推导语义独立。
- **114 条没有精确匹配**：仅表示未在三次历史 Trainer 中出现逐字相同的目标文本；并不是独立新 Held-out、可用新训练数据或独立审阅批准名单。Gold195 本身为历史开发暴露池。
- **训练样本改进：** 需目标时点故事卡、权利、年龄/同意、安全边界、双 Reviewer 独立判定、Train/Validation world-component 分离与 Owner 签核。这些步骤都尚未执行。
- **R55**：4 条 HOLD 与 79/69/4 冻结统计继续保留；`Dataset v0.4` 准入为 0；不触碰 R50，不跑 HF/GPU，不改 `main`。

此工具只有精确目标归属标注能力，不自动筛出 v0.4 训练集。
