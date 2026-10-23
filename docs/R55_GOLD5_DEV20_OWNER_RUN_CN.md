# R55 原始 Gold 五方开发集评估 — Owner Mac 本地指南

**当前状态：只交付预检/构包代码；没有真实私有数据运行，也未完成五方盲评。** 本工具只处理 R47/R48/R55 已曝光的旧 20 题，不能触碰 R50，也不能作为正式 Held-out 晋升证据。

## 重要依据与范围

- R48 的原始 Gold 来自 `data/compiled/v0.3/test.jsonl`，不是 Gold195 随机抽取；使用 `scripts/v02_r48_four_arm_build.py` 中原有 `read_gold()`，强制逐条与 `evaluations/v0.1/test/prompts.jsonl` 的完整历史/角色一致。
- Base、v0.1、v0.2：原有 R47 三臂结果 `base-results.jsonl`、`v01-results.jsonl`、`v02-results.jsonl`，以及 `R47_PRIVATE_RUN_REPORT.json`；沿用 `check_r47()` 严格验证冻结 SHA、run key 和提示一致。
- v0.3-A：R55 新 20 条回复，与冻结的 R55 结果 SHA256 `80586435b4b8dbe361d2e76d746a1e0e88154d08525d63720562810efa186557` 对应；R55 原始私有运行报告 SHA256 `924404daa12ed5886a879e4445b7995350228f559995f646d480859f76c4fd64`。**不接受相似名称的其他推理输出。**
- 旧 20 题来自**两个**已曝光世界；同一组题跨 R47/R48/R55 重用，绝非新的独立测试。R54 checkpoint-16 仍 NO-GO 正式 R50。

## 1. 安装安全代码到 Git 仓库

```bash
set -euo pipefail
cd ~/workspace/storyforge
git switch main
git pull --ff-only origin main
# 如果用户下载的是 PATCH：
git apply --check ~/Downloads/StoryForge_R55_GOLD5_DEV20_NOJOB_20261023.patch
git apply ~/Downloads/StoryForge_R55_GOLD5_DEV20_NOJOB_20261023.patch
python3 -m unittest discover -s tests -p 'test_v03_r55_gold5_build.py' -v
# 检查 Git diff 确认只有脚本、测试、README；不要 git add -A
```

## 2. 指定已有的实际 R47/R55 文件

**以下文件名是已核对的 R47 规范名称；本地目录要按 Mac 实际位置选择。** 不推断某个不存在的本地路径，更不要使用 R50 文件或 R55 匿名评审的 Left/Right 文本代替已冻结原始模型输出。

```bash
cd ~/workspace/storyforge

R47_DIR="/ABSOLUTE/EXISTING/PRIVATE/R47_RESULT_DIRECTORY"
R55_DIR="/ABSOLUTE/EXISTING/PRIVATE/R55_RESULT_DIRECTORY"

# 以下结果文件一旦找到，必须指向其实际字节文件。
BASE="$R47_DIR/base-results.jsonl"
V01="$R47_DIR/v01-results.jsonl"
V02="$R47_DIR/v02-results.jsonl"
R47_REPORT="$R47_DIR/R47_PRIVATE_RUN_REPORT.json"
V03="$R55_DIR/ACTUAL_R55_V03_20_RESPONSES.jsonl"
R55_REPORT="$R55_DIR/ACTUAL_R55_RUN_REPORT_PRIVATE.json"

# 仅本地查看候选文件路径（无需输出文件内容）
find "$HOME/.local/share/storyforge/r55" "$HOME/.local/share/storyforge/r47" \
    -type f \( -name '*results.jsonl' -o -name '*REPORT*json' \) -print 2>/dev/null || true
```

> R55 的生成结果**不能**使用任何未经 SHA 确认的临时文件。实际文件名可能并非上述示意名；设定准确的 `V03` 与 `R55_REPORT` 后由代码验证哈希即可。若文件只在私有 HF Bucket，使用已有授权 HF CLI **只读下载**。本工具不会连接 HF。

## 3. 只做预检，绝不创建输出

```bash
BASE_DIR="$HOME/.local/share/storyforge/r55/gold5-dev20"
OUT="$BASE_DIR/owner-pack-v1"

COMMON=(
  --compiled-test data/compiled/v0.3/test.jsonl
  --prompts evaluations/v0.1/test/prompts.jsonl
  --manifest evaluations/v0.1/test/manifest.json
  --r47-report "$R47_REPORT"
  --base "$BASE"
  --v01 "$V01"
  --v02 "$V02"
  --v03 "$V03"
  --r55-report "$R55_REPORT"
  --output-dir "$OUT"
)
python3 scripts/v03_r55_gold5_build.py "${COMMON[@]}" --mode preflight
```

成功：

```text
R55_GOLD5_20_CASE_FIVE_SOURCE_EXACT_ALIGNMENT_PASS__NO_OUTPUT__NO_GPU
R55_GOLD5_FROZEN_PROMPT_AND_GOLD_AND_MODEL_BYTES_MATCHED
```

若报 `R55_GOLD5_HOLD__...`，保留 HOLD，**不复制内容、不重跑模型、不修改冻结输入**。特别是 R55 新输出必须使用原生 `messages` + `response` JSONL，原样输入与冻结提示匹配；任何格式不符先只做私有结构诊断，不放宽校验。

## 4. 预检成功后生成私有盲审包

```bash
umask 077
python3 scripts/v03_r55_gold5_build.py "${COMMON[@]}" --mode build
cat "$OUT/R55_GOLD5_PREP_SAFE_COUNT_ONLY.json"
```

输出目录绝不能位于 Git 仓库，不能已存在。生成：
- `reviewers/R55_GOLD5_PAIR_Reviewer_{01,02,03}_PRIVATE.csv`：**先发**给三位 Reviewer 的独立 v0.3-A vs v0.2 匿名成对任务。
- `reviewers/R55_GOLD5_FIVE_Reviewer_{01,02,03}_PRIVATE.csv`：后发的 Gold + 四模型五方评分任务。
- `coordinator/private/R55_GOLD5_COORDINATOR_KEY_PRIVATE.json`：身份映射与源答案 SHA，**永远只在 Owner/coordinator 端**。
- `R55_GOLD5_PREP_SAFE_COUNT_ONLY.json`：唯一建议发回这里的回执；包含哈希/计数，不含故事原文、模型回复或身份映射。

每位 Reviewer 对五份匿名回复分别做六维评分，Gold **不是**正确答案豁免。成对表与五方表分别评分，不从五方“最佳”反推出直接胜率。Reviewers 不得看 R48/R55 历史评分、解盲答案键或模型身份；若使用远端 AI Reviewer，原始文字会离开本机，需 Owner 另行明确同意。不要将私有 CSV 上传普通 Git。

## 5. 结果不等于正式结论

本次构包只确认 20/20 旧题的五方原文一一对齐；不是新一轮 Reviewer 评分，也不会替代 R55 现有 NO-GO。新五方评分完成并冻结之后，才可以据此给出新的**开发集** GO/NO-GO 建议。R50 正式准入 0、未 sealed、无付费 GPU/CPU Job、无模型推理、无重训。
