# StoryForge R57 — Owner Mac 执行清单：G2 实际八源回放

**2026-10-26。安全边界：** 只读核验真实原始文件，回执只含统计结果；不触碰 R50，不启动 HF CPU/GPU、不训练、不晋升、不修改 R55 4 HOLD、不自动合并 PR。

## A. 更新已存在的工作仓库（禁止丢弃本地修改）

在 Mac 的 Terminal/zsh 中输入。把第一行路径调整为实际已存在的 StoryForge clone；若不确定，可在已经打开的仓库终端直接执行 `pwd`，无需新建仓库。

```zsh
cd "$HOME/workspace/storyforge-r55-tooling" || exit 1
git status --short
# 上一条如显示本地尚未提交的内容，请先处理，不执行覆盖或 reset
git fetch origin r57/v03b-data-design
git switch r57/v03b-data-design
git pull --ff-only origin r57/v03b-data-design
python3 --version
```

若拉取失败（网络或工作区冲突），应停止，不要 `reset --hard`。

## B. 零写入预检：可立即运行

```zsh
PRIVATE="$HOME/.local/share/storyforge/r57/private"
umask 077
mkdir -p "$PRIVATE/r46" "$PRIVATE/r54"
chmod 700 "$PRIVATE" "$PRIVATE/r46" "$PRIVATE/r54"

# 只校验固定四份 Git 原始文件：正常返回 0
python3 scripts/r57_g2_mac_preflight.py --repo-root "$PWD" --only-public

# 八份完整校验：若 R46/R54 尚未准备，返回代码 2 = HOLD（正常阻断）
python3 scripts/r57_g2_mac_preflight.py --repo-root "$PWD" --private-root "$PRIVATE"
```

结果只显示每个固定组名对应 `BYTE_PIN_PASS` / `MISSING` / `BYTE_PIN_MISMATCH` / `UNSAFE_OR_UNREADABLE`，并标记 `training_authorized=false`。不搜索任何目录，也不读取 R50。

## C. 四份 Owner 私有 Trainer JSONL 的放置方法（有正版文件时才做）

下面四行变量必须换成**实际已经存在且经过 Owner 来源核验**的历史 `compiled Trainer` JSONL 绝对路径，不能填写 R45/R53 的另一个阶段、重建的摘要文件、Zip 容器或 R50 文件：

```zsh
R46_TRAIN_ORIGINAL="/填写真正的/R46/compiled/train.jsonl"
R46_VAL_ORIGINAL="/填写真正的/R46/compiled/validation.jsonl"
R54_TRAIN_ORIGINAL="/填写真正的/R54/compiled/train.jsonl"
R54_VAL_ORIGINAL="/填写真正的/R54/compiled/validation.jsonl"
```

先对原始文件做 SHA256；期望如下：

| 编译后文件 | 预期 SHA256 |
|---|---|
| R46 Train49 | `a028bf9fb28b12b4a3fa352d6a60281bd9e1ef5773ebfdfecc7ac80eb2cba517` |
| R46 Val15 | `cc8d647471423f4969149f8cabdea980aad15d8bd4424d9dd98da3313c639f3c` |
| R54 Train31 | `d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7` |
| R54 Val9 | `b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d` |

```zsh
shasum -a 256 "$R46_TRAIN_ORIGINAL"
shasum -a 256 "$R46_VAL_ORIGINAL"
shasum -a 256 "$R54_TRAIN_ORIGINAL"
shasum -a 256 "$R54_VAL_ORIGINAL"
```

确认每份 SHA256 完全匹配后，执行**只新建、不覆盖**的私有目录拷贝（macOS `cp -n`）：

```zsh
cp -n "$R46_TRAIN_ORIGINAL" "$PRIVATE/r46/train.jsonl"
cp -n "$R46_VAL_ORIGINAL" "$PRIVATE/r46/validation.jsonl"
cp -n "$R54_TRAIN_ORIGINAL" "$PRIVATE/r54/train.jsonl"
cp -n "$R54_VAL_ORIGINAL" "$PRIVATE/r54/validation.jsonl"
chmod 600 "$PRIVATE/r46/"*.jsonl "$PRIVATE/r54/"*.jsonl

python3 scripts/r57_g2_mac_preflight.py --repo-root "$PWD" --private-root "$PRIVATE"
```

如果目的位置已经存在，`cp -n` 会跳过而不覆盖；因此最后一次预检必不可少。若任何一项不是 `BYTE_PIN_PASS`，立即 HOLD，禁止继续完整回放。

**不要将四份私有文件拷贝到 Git 仓库内；不要把逐条哈希、角色卡、别名图或训练原文上传到聊天/PR。**

## D. 八源真实交叉回放（八个 BYTE_PIN_PASS 后）

```zsh
python3 -m unittest discover -s tests -p 'test_r57_*.py' -v

python3 scripts/r57_trainer_exact_replay.py \
  --repo-root "$PWD" --private-root "$PRIVATE" --mode full \
  --source GOLD87 --source GOLD108 \
  --source V01_TRAIN --source V01_VALIDATION \
  --source R46_TRAIN --source R46_VALIDATION \
  --source R54_TRAIN --source R54_VALIDATION \
  --safe-out "$PRIVATE/R57_G2_EIGHT_SOURCE_EXACT_SAFE_$(date +%Y%m%d_%H%M%S).json"
```

该回放仅计算并输出脱敏计数。**不会**认证世界/角色别名图或 Dataset v0.4 个案准入；R54↔R46 的旧 14/9/8 若不能从真实八源重放，命令会直接 HOLD，且不会伪造结果。

## E. 返回给 ChatGPT 的最小安全材料

你可以直接粘贴 B 的 JSON 状态，或 D 的**统计 JSON**（先人工确认没有敏感值）。不要提交 `PRIVATE` 内的原始 JSONL、实际 SHA 列表、逐条世界 token、HF 凭证、R50 或任何原始故事文本。

只有八源精确重放 PASS 后，才开始世界别名/角色连通图的独立审核与 G3 人工候选审核；四项 R55 HOLD 不改变。
