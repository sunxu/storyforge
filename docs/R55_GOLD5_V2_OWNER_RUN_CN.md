# R55 五方开发盲评 v2：Owner 执行步骤

**本修复原因：** v1 五方表中的 `四模型最佳(请填写对应匿名字母或TIE)` 要求盲评者知道 Gold 身份，违反盲态。v2 创建三种互相独立的匿名任务：Pair(2)、Four(4)、Five(5)。保留原来的 `owner-pack-v1` 原封不动，**不要给 Reviewer 发送 v1 CSV**。

## 安装与合成测试

```bash
cd ~/workspace/storyforge
# 将补丁放到 ~/Downloads 下
# 检查工作树状态，避免碰触本地未提交改动
git apply --check ~/Downloads/StoryForge_R55_GOLD5_V2_BLIND_FIX_20261023.patch
git apply ~/Downloads/StoryForge_R55_GOLD5_V2_BLIND_FIX_20261023.patch
python3 -m unittest discover -s tests -p 'test_v03_r55_gold5_review_v2.py' -v
```

## 真实数据重验并在新的私有目录中构建

```bash
set -euo pipefail
umask 077
cd ~/workspace/storyforge
R47_DIR="$HOME/.local/share/storyforge/r47/r47-20261014T091647Z-637890/coordinator"
R55_DIR="$HOME/.local/share/storyforge/r55/inference-results/r55-dev-20261022T023436Z-188604"
OUT="$HOME/.local/share/storyforge/r55/gold5-dev20/owner-pack-v2"
COMMON=(
  --compiled-test data/compiled/v0.3/test.jsonl
  --prompts evaluations/v0.1/test/prompts.jsonl
  --manifest evaluations/v0.1/test/manifest.json
  --r47-report "$R47_DIR/R47_PRIVATE_RUN_REPORT.json"
  --base "$R47_DIR/base-results.jsonl"
  --v01 "$R47_DIR/v01-results.jsonl"
  --v02 "$R47_DIR/v02-results.jsonl"
  --v03 "$R55_DIR/r54-results.jsonl"
  --r55-report "$R55_DIR/R55_R54_INFERENCE_REPORT_PRIVATE.json"
  --output-dir "$OUT"
)
python3 scripts/v03_r55_gold5_review_v2.py "${COMMON[@]}" --mode preflight
python3 scripts/v03_r55_gold5_review_v2.py "${COMMON[@]}" --mode build
cat "$OUT/R55_GOLD5_V2_PREP_SAFE_COUNT_ONLY.json"
```

预期终端状态：
- `R55_GOLD5_V2_20_EXACT_SOURCES_PASS__NO_OUTPUT__NO_JOB`
- `R55_GOLD5_V2_THREE_DISTINCT_BLIND_TASKS_PREPARED__DEV_ONLY__NO_R50`

输出：9 份 Reviewer CSV（Pair、Four、Five × 3），一个只由 Owner 保存的私有答案映射，1 份可共享脱敏回执。输出目录必须尚不存在，脚本拒绝覆盖。

脚本只使用 Python 标准库及原仓库源代码，不需要 GPU、HF Job、模型推理；没有更改任何已冻结原件。真实输入不匹配时只会显示 `R55_GOLD5_V2_HOLD__...`，不要强行放宽校验。
