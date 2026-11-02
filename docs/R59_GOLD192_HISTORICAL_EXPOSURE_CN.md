# R59 Gold192 历史目标曝光核验（Owner Mac）

## 当前状态

Pilot-7 已完成：Gold192 192/192 `EXACT_MATCH`，上下文 7/7 导出。
这不代表 Quality-v1 准入。下一步先核验 Gold192 目标回复是否已进入历史 Train / Validation / Test。

## 工具与复用

入口：`experiments/r58_quality/r59_gold192_historical_exposure.py`。

该工具复用：
- `scripts/r57_source_index_export.py` 的固定源路径与安全读取；
- `scripts/r57_trainer_exact_replay.py` 的 SHA256 pin、JSONL 结构和目标回复精确哈希；
- `scripts/r57_g3_private_exposure_ledger.py` 的 Gold195 历史 81 条曝光基线重放。

额外核验 `data/compiled/v0.3/test.jsonl`（20 条，独立 SHA256 + Git blob pin）。
**Test 范围明确仅为 v0.3 compiled test；SAFE 的 `test_exposure_scope_complete` 固定为 false，不会冒称已覆盖所有历史评测工件。**

## Mac 执行

```bash
set -euo pipefail

REPO="$HOME/workspace/storyforge-gold-quality"
R57_PRIVATE="$HOME/.local/share/storyforge/r57/private"
R59_PRIVATE="$HOME/.local/share/storyforge/r59/private"
PACKETS="$R59_PRIVATE/GOLD192_STORY_REVIEW_PACKETS_PRIVATE.jsonl"
OUT="$R59_PRIVATE/r59-history-exposure-v1"

cd "$REPO"

# 使用项目内已有 Python 环境；该工具只需要标准库
PY=""
for candidate in "$REPO/.venv/bin/python" "$REPO/venv/bin/python" "$REPO/env/bin/python"; do
  if [ -x "$candidate" ]; then PY="$candidate"; break; fi
done
test -n "$PY"
"$PY" --version

# 只读核对输入存在；R46/R54 私有历史 Trainer 文件必须齐全
test -f "$PACKETS"
for rel in r46/train.jsonl r46/validation.jsonl r54/train.jsonl r54/validation.jsonl; do
  test -f "$R57_PRIVATE/$rel" || { echo "MISSING_HISTORICAL_SOURCE: $rel"; exit 1; }
done
test ! -e "$OUT"

# 执行固定 SHA / Git blob pin 校验和逐目标精确曝光分类
"$PY" experiments/r58_quality/r59_gold192_historical_exposure.py \
  --repo-root "$REPO" \
  --private-root "$R57_PRIVATE" \
  --source-packets "$PACKETS" \
  --output-dir "$OUT"

# SAFE 及私有 ledger SHA；不要上传 PRIVATE JSONL
"$PY" -m json.tool "$OUT/R59_GOLD192_HISTORICAL_EXPOSURE_SAFE.json"
shasum -a 256 "$OUT/R59_GOLD192_HISTORICAL_EXPOSURE_PRIVATE.jsonl" \
  "$OUT/R59_GOLD192_HISTORICAL_EXPOSURE_SAFE.json"
```

## 结果解释

SAFE 报告：
- `gold192_train_exposed`：目标精确出现在 V01/R46/R54 历史 Train 的案例数；
- `gold192_validation_exposed`：目标精确出现在历史 Validation 的案例数；
- `gold192_test_exposed`：目标精确出现在 v0.3 compiled Test 的案例数；
- `gold192_not_found_in_pinned_history`：仅表示在本工具完整固定的上述来源中未发现精确目标哈希；
- `test_exposure_scope_complete=false`：不覆盖未纳入固定源的其他历史评测包。

工具同时复现 Gold195 历史基线：ever-Train 66、ever-Validation 24（交集 9，union 81）。
任一源 pin、基线数量或输入结构不符均 fail-closed，不生成准入结论。

输出仅在 Owner 私有目录，create-only、0600；不改写 Gold 冻结源、审核文件或历史训练文件。不访问 R50、不连接 Supabase、不启动 HF Job/GPU。


## SHA pin HOLD 排查

如果返回 `V03_TEST_SHA256_MISMATCH` 或 `V03_TEST_GIT_BLOB_MISMATCH`，不要改写 Test 文件或放宽校验。先在 Owner Mac 执行以下只读诊断：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-gold-quality"
P="data/compiled/v0.3/test.jsonl"

echo "=== CHECKOUT ==="
git branch --show-current
git rev-parse HEAD
git status --short -- "$P"

echo "=== COMMITTED TREE BLOB ==="
git ls-tree HEAD -- "$P"
git show "HEAD:$P" | shasum -a 256

echo "=== WORKTREE FILE ==="
shasum -a 256 "$P"
git hash-object "$P"

echo "=== PIN CONSTANTS ==="
grep -E '^V03_TEST_(SHA256|GIT_BLOB|PATH) =' \
  experiments/r58_quality/r59_gold192_historical_exposure.py
```

当前 GitHub `gold-quality/unified-pipeline-v1` 已独立复核的权威值：
- Git blob：`c17f225967b6b2f8cbaf3d82fadac1b4031d0654`
- SHA256：`d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d`
- 记录数：20

判读：
- `git ls-tree` 的 blob 不同：本地 HEAD 不是包含该冻结 Test 的版本，先核对分支与提交。
- `git ls-tree` 正确但 `git show` 的 SHA 不同：本地 Git 对象或读取路径异常，先停止并调查。
- `git show` 的 SHA 正确但工作区 SHA 不同：本地文件被修改、换行转换或过滤器改写；不要覆盖，先保留差异并查明来源。
- 两个 SHA 都正确但脚本仍 HOLD：检查实际运行的脚本常量、`--repo-root` 指向和 Python 导入路径，避免执行另一份工作区代码。

诊断只输出公开冻结文件的哈希与 Git 元数据，不要输出 JSONL 内容。确认工作区恢复到冻结字节后，再使用新的空输出目录重跑；旧输出若已存在，不要覆盖。
