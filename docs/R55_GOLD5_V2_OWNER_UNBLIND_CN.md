# StoryForge R55 Gold5 v2 — Owner 本地最终解盲与统计指南

**用途：** 三轮匿名评分（Pair/Four/Five）都已经以无答案映射方式冻结后，在 Owner 私有 Mac 上校验并进行一次受控解盲。仅旧 R47/R48/R55 的 **20 题、2 个已经曝光故事世界**；不是 R50，也不授权模型晋升或 GPU。

## 本次精确输入 SHA 已内置

- v2 构包回执 SHA256：`6476da25e7d6b043a7bec3d413bfc75885c8571c188f318e3a4eb523888bdaa4`。
- 私有五方/四模型/成对映射 SHA256：`fc328688fac957c849d822d82db841479105afb0c885b48b381b1a270f9f3334`。
- Pair 三份评分文件哈希：`00fb53854b...`、`e7de4f91...`、`f800281f...`（脚本保存完整 64 位）。
- Four 三份评分文件哈希：`12d48350...`、`8bcb9544...`、`1eb51a10...`。
- Five 三份评分文件哈希：`3ac83edc...`、`9e47b511...`、`b6bca635...`。
- 预期评分格：Pair 720、Four 1440、Five 1800，总数 3960。旗标存在的 Reviewer×case 行：Pair 32、Four 50、Five 50。**旗标未逐事件确认，不等于违规数。**

脚本使用 stdlib 及已经运行过的 `scripts/v03_r55_gold5_review_freeze.py`，不会重新运行模型，也不会修改原始冻结表。`verify` 不打开身份映射。`unblind` 先重新检查全部三个回执、九份私有冻结 CSV 与既有空白原件，再检查私有映射 SHA256 与每题每条匿名回复的字节哈希；任何不一致即 HOLD。仅成功通过后在新的私有目录写入 Owner 结果。

## 1. 安装工具和合成测试

```bash
set -euo pipefail
cd ~/workspace/storyforge

git apply --check "$HOME/Downloads/StoryForge_R55_GOLD5_V2_OWNER_UNBLIND_NOJOB_20261023.patch"
git apply "$HOME/Downloads/StoryForge_R55_GOLD5_V2_OWNER_UNBLIND_NOJOB_20261023.patch"

python3 -m unittest discover -s tests -p 'test_v03_r55_gold5_owner_unblind.py' -v
# 期待 Ran 17 tests ... OK
```

如果脚本或路径已存在，补丁拒绝重复添加；不要覆盖旧版文件。代码提交只用显式 `git add scripts/v03_r55_gold5_owner_unblind.py tests/test_v03_r55_gold5_owner_unblind.py docs/R55_GOLD5_V2_OWNER_UNBLIND_CN.md`。不要添加私有 CSV / KEY / 输出目录。

## 2. 在 Owner Mac 上先只验证三轮数据，不读取 KEY

```bash
set -euo pipefail
umask 077
cd ~/workspace/storyforge
ROOT="$HOME/.local/share/storyforge/r55/gold5-dev20"
OUT="$ROOT/owner-unblind-v1"
ARGS=(
  --pack "$ROOT/owner-pack-v2"
  --pair-dir "$ROOT/frozen/pair-v1"
  --four-dir "$ROOT/frozen/four-v1"
  --five-dir "$ROOT/frozen/five-v1"
  --out-dir "$OUT"
)

python3 scripts/v03_r55_gold5_owner_unblind.py \
  "${ARGS[@]}" --mode verify
```

成功标记：`R55_GOLD5_V2_ALL_3_ROUNDS_3960_RATINGS_VERIFIED__KEY_NOT_READ__NO_R50`。若 HOLD，不应修改任何已经冻结的输入或密钥；只检查本地路径或是否不慎提交了错误版本。请只反馈 HOLD 代码，避免发送内容。

## 3. 全部 verify PASS 后 Owner 执行一次解盲

在**同一 shell**、且 `ARGS` 仍定义时：

```bash
python3 scripts/v03_r55_gold5_owner_unblind.py \
  "${ARGS[@]}" --mode unblind

cat "$OUT/R55_GOLD5_V2_OWNER_UNBLIND_SAFE_AGGREGATE.json"
```

成功标记：`R55_GOLD5_V2_OWNER_ONLY_UNBLIND_AGGREGATED__DEVELOPMENT_ONLY__NO_R50`。

Owner 输出：

- **可共享的脱敏统计**：`R55_GOLD5_V2_OWNER_UNBLIND_SAFE_AGGREGATE.json`。包含 Pair/Four/Five 三组分别计算的模型偏好票、20 题多数票、六维均分、未经仲裁的 Reviewer×case×arm 旗标数量及其对应的去重题目计数、验证 SHA256。**不含故事、私有 case ID 或具体回复正文**。
- **仅 Owner 保管的逐题核查索引**：`R55_GOLD5_V2_OWNER_UNBLIND_CASE_PRIVATE.json`。含逐题 case ID、模型映射后的评审偏好、每维分数、待审问题对应的私有原 CSV 行位置。不含复制的全文，但可能泄露逐题评估身份，**不可提交普通 Git 或发给盲审 Reviewer**。
- **原 Coordinator KEY**：保持在 `owner-pack-v2/coordinator/private/R55_GOLD5_COORDINATOR_KEY_V2_PRIVATE.json`，工具只读取，不复制、不修改、不删除。

所有生成文件保存在 `~/.local/share/storyforge/`，输出目录必须事先不存在，私有目录权限 0700，新 JSON 文件权限 0600，失败不会启动 HF/模型/网络操作。

## 4. 三轮评估怎样计算及如何解读

- Pair 的主要结论是独立录入的 `v0.3-A vs v0.2` 偏好，**不可由 Five/Four 重新推导**。按题统计三名 Reviewer 是否有至少 2 人给出同一最佳；三人三种选择或 1–1–1 归入 `SPLIT_NO_MAJORITY`。Pair 排除分母时，TIE/SPLIT 应另报，并披露分母。
- Four 统计四个模型的独立最佳票，Five 统计含 Original Gold 的五份回复。Gold 是历史原始参考回复，不是第五模型，也不自动正确。
- 每一来源的六维均分是每题每位 Reviewer 的 **1–5 评分平均**。不同评估轮次应分别报告，不把旧 R48/R55 轮次分数混算。
- 旗标仅是 Reviewer 标注的待验证事件：在宣布确证玩家自主权违规/禁句前，需核对冻结回复、世界设定、证据和标记位置，并进行独立仲裁。单条题目上三人打旗标绝不等于三道新题。
- 整个流程仍是只对 **2 个已曝光故事世界/20 道题** 进行开发评估，证据无法证明 v0.3-A 在新世界中的泛化。**即使本次五方指标优于 v0.2，也不能直接批准 R54 晋升或开放 R50**。

## 5. 下一步

将**仅脱敏** `R55_GOLD5_V2_OWNER_UNBLIND_SAFE_AGGREGATE.json` 送交此对话作跨三轮差异分析。随后对标记的候选严重问题逐事件在 Owner 私有环境核对，再做正式候选 GO/NO-GO 复审。不要向已经参与盲审的 Reviewer 发送映射。
