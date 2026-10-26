# StoryForge R55 Gold5 v2 — Owner 端三轮盲审发放与冻结

**状态：工具测试通过（25/25 synthetic），真实 Reviewer 已评分 CSV 尚未收到。** 全流程仅旧 20 题、两个已曝光世界，属于开发集。R50 不访问，R54 不晋升，不执行任何 HF/GPU/模型推理。

## 1. 先只发第一轮 Pair（成对）

在 Mac 的 `~/workspace/storyforge`：

```bash
set -euo pipefail
umask 077
cd ~/workspace/storyforge
PACK="$HOME/.local/share/storyforge/r55/gold5-dev20/owner-pack-v2"
python3 -m unittest discover -s tests -p 'test_v03_r55_gold5_review_freeze.py' -v

# 只核对第一轮 3 张 pristine 表；绝不输出故事正文
python3 - "$PACK" <<'PY'
import pathlib,hashlib,json,sys
p=pathlib.Path(sys.argv[1]); r=json.loads((p/'R55_GOLD5_V2_PREP_SAFE_COUNT_ONLY.json').read_text())
assert r['case_count']==20 and r['reviewers_completed']==0
assert r['status']=='R55_GOLD5_V2_THREE_DISTINCT_BLIND_TASKS_PREPARED__DEV_ONLY__NO_R50'
for i in (1,2,3):
    n=f'R55_GOLD5_PAIR_V2_Reviewer_{i:02d}_PRIVATE.csv'
    f=p/'reviewers'/n
    assert f.is_file() and not f.is_symlink()
    assert hashlib.sha256(f.read_bytes()).hexdigest()==r['reviewer_private_csv_sha256'][n]
    print('PRISTINE_PAIR_READY',i, n)
PY
```

分别只向三位独立 Reviewer 提供：
- Reviewer 01: `owner-pack-v2/reviewers/R55_GOLD5_PAIR_V2_Reviewer_01_PRIVATE.csv`
- Reviewer 02: `owner-pack-v2/reviewers/R55_GOLD5_PAIR_V2_Reviewer_02_PRIVATE.csv`
- Reviewer 03: `owner-pack-v2/reviewers/R55_GOLD5_PAIR_V2_Reviewer_03_PRIVATE.csv`

附 `docs/R55_GOLD5_V2_REVIEWER_PROTOCOL_CN.md`，**不要**附 `coordinator/private`、五方/四方表、R47/R48/R55 旧评分、模型来源标签、原始 Gold 身份。保存返还版 CSV 到单独目录，不覆盖 pristine 原件。若远端 AI Reviewer 参与，故事原文和模型回复将发送到该服务，需要 Owner 明确授权，且三人的独立身份需如实记录。以前参与过相同旧 20 题评分的 Reviewer 不能声称“未暴露”。

## 2. 收齐三份完成版后先冻结 Pair

将三个完成版分别保存为 `reviewer-01.csv`, `reviewer-02.csv`, `reviewer-03.csv` 于个人私有路径（路径仅示意，可自选）；按顺序对应 Reviewer 01/02/03：

```bash
PACK="$HOME/.local/share/storyforge/r55/gold5-dev20/owner-pack-v2"
ROOT="$HOME/.local/share/storyforge/r55/gold5-dev20"

python3 scripts/v03_r55_gold5_review_freeze.py \
  --pack "$PACK" \
  --round pair \
  --completed \
     "$ROOT/completed/pair/reviewer-01.csv" \
     "$ROOT/completed/pair/reviewer-02.csv" \
     "$ROOT/completed/pair/reviewer-03.csv" \
  --output-dir "$ROOT/frozen/pair-v1"

cat "$ROOT/frozen/pair-v1/R55_GOLD5_V2_ROUND_FREEZE_SAFE.json"
```

成功：`R55_GOLD5_V2_PAIR_3_REVIEWERS_FROZEN__KEY_NOT_READ__NO_R50`，72×10=720 个有效评分格，三位 Reviewer 独立 CSV 字节 SHA 分别固定。失败将显示 `R55_GOLD5_V2_FREEZE_HOLD__<安全错误代码>`，不会输出题文或把数据写进仓库；修复已完成文件后重试（不可修改 pristine）。

## 3. 后续轮次顺序（不要现在发）

**四模型轮**：Pair 三份完整冻结后，分别发送三份 `R55_GOLD5_FOUR_V2_Reviewer_0N_PRIVATE.csv`；完成并逐字核验后执行（仍无模型推理）：

```bash
python3 scripts/v03_r55_gold5_review_freeze.py \
  --pack "$PACK" --round four \
  --prior-pair-freeze "$ROOT/frozen/pair-v1/R55_GOLD5_V2_ROUND_FREEZE_SAFE.json" \
  --completed \
    "$ROOT/completed/four/reviewer-01.csv" \
    "$ROOT/completed/four/reviewer-02.csv" \
    "$ROOT/completed/four/reviewer-03.csv" \
  --output-dir "$ROOT/frozen/four-v1"
```

成功冻结 1440 个评分格。

**五方轮**：Four 冻结后才发送 `R55_GOLD5_FIVE_V2_Reviewer_0N_PRIVATE.csv`（其中有匿名 Original Gold）；完成：

```bash
python3 scripts/v03_r55_gold5_review_freeze.py \
  --pack "$PACK" --round five \
  --prior-pair-freeze "$ROOT/frozen/pair-v1/R55_GOLD5_V2_ROUND_FREEZE_SAFE.json" \
  --prior-four-freeze "$ROOT/frozen/four-v1/R55_GOLD5_V2_ROUND_FREEZE_SAFE.json" \
  --completed \
    "$ROOT/completed/five/reviewer-01.csv" \
    "$ROOT/completed/five/reviewer-02.csv" \
    "$ROOT/completed/five/reviewer-03.csv" \
  --output-dir "$ROOT/frozen/five-v1"
```

成功冻结 1800 个评分格。三轮总评分格：3960。只有所有原始评分文件和 safe 冻结回执固定之后，**才可以**由 Owner/协调员在单独控制的环境读取私有答案映射、计算三种互不混淆的聚合。不要从五方结果反推成对胜率。

## 4. 冻结工具边界

- 直接复用 `owner-pack-v2` 的原始空白表与安全回执，逐字核对每条的来源输入和匿名回复完全不变，20 行顺序与 6 维 1–5 分值齐全。所有偏好、严重标记与非空理由必须齐全，含严重标记必须提供证据。
- **不声称**对理由的事实真伪或 Reviewer 人员独立性自动认证；仅能核验结构、计数和完整性。三份评分表内容应独立撰写，工具拒绝字节完全相同的三个“完成文件”。
- `freeze` 产生私有评分快照（0600 创建后设为 0400）和脱敏 `R55_GOLD5_V2_ROUND_FREEZE_SAFE.json`，不能覆盖已有目录，**不读取协调员身份映射**，也不作解盲。
- 请只分享脱敏 JSON 或终端 PASS/HOLD 标记，**不要**把私有 CSV/答案密钥传到 GitHub、普通 CI、公开渠道或模型开发群。
- 当前历史旧 20 题仍属于开发集，正式独立 R50 仍无准入；R55 checkpoint-16 的 NO-GO 状态不会因构包与空白评分冻结准备而自动改变。
