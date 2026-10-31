# StoryForge R58 G1 — 旧 DEV20 2 个世界精确 UUID 本地核验（SAFE）

## 状态及数据纪律

2026-10-31。仅编写并在隔离环境通过 **14 项合成测试**；Owner Mac 的真实固定来源与私有账本尚未执行。R58 G1 仍为 **HOLD**，Train / Validation / Teacher 准入始终为 0。无 GPU、无 HF Job、无数据库操作、无 PR 合并。

本工具覆盖的是 R47/R48/R55/R57 复用的同一个 **v0.1 Test / 20 题 / 2 世界**。它不是 R50，也不是 Gold195，不覆盖其他旧开发目标或保护/留出世界，不证明历史训练来源清单完整。

### 来源固定证据（仅从 owner 本地 Git 对象读取）

- 原始 `data/compiled/v0.3/test.jsonl` Git Blob SHA-1 `c17f225967b6b2f8cbaf3d82fadac1b4031d0654`，文件 SHA-256 `d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d`。
- `evaluations/v0.1/test/manifest.json` Git Blob SHA-1 `f4e39196c6aa0a87b095d7de5cae4acd8b2fca63`，20 题行号与提示摘要。
- 历史冻结跨产物审计 `docs/evidence/V01_CROSS_ARTIFACT_AUDIT_20261010.json` Git Blob SHA-1 `2e7041c9b2b417c16f926115212157648c8f8406`，已有 Test 20/20 对齐回执。
- `data/compiled/v0.3/budget_report.json` Git Blob SHA-1 `8d4b35001a6533972e001736b769b630508941b6`，附加来源世界元数据交叉核验。

工具先检查 Test 全文件 SHA256，再从 **本机**冻结 JSONL 的字节流仅提取 `metadata.story_id` 与 `id` 结构字段；不会解析 `messages` 数组，不打印、发送或写出叙事正文。注意：为执行来源完整性校验，本机仍需读取 Test 文件**原始字节**，这与完全不触及 Test 文件不同；不允许上传这些原始字节到聊天或 GitHub。**绝不访问 R50 保护题目或来源正文。**

它从三份既有私有账本核对原五条、历史 SFT 1 条排除、R50 和 Gold195 各 0 条命中，检查旧 DEV20 精确 UUID 交集；只写一个新建的权限 0600 私有逐条结果，并在终端只打印无 UUID 的 SAFE JSON。校验失败或目标文件已存在时退出码 42 或操作系统错误，保持 HOLD，不自动恢复或覆盖。

## Mac Owner 操作

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only

# 先确保文件不是已存在的版本；不要覆盖历史工具
for f in check_legacy_dev20_uuid.py test_check_legacy_dev20_uuid.py; do
  test ! -e "experiments/r58_round1/$f" || { echo "HOLD: $f exists"; exit 42; }
done

# 按下载后实际的 ZIP 文件路径修改以下变量
ZIP="$HOME/Downloads/StoryForge_R58_G1_OLD_DEV20_UUID_NOJOB_20261031.zip"
unzip -j -n "$ZIP" check_legacy_dev20_uuid.py test_check_legacy_dev20_uuid.py \
  -d experiments/r58_round1/

# 新增14项纯合成单元测试；如旧版仍是97项，合计预期111项
python3 -m unittest discover -s experiments/r58_round1 -p 'test_*.py' -v &&

ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
umask 077
python3 experiments/r58_round1/check_legacy_dev20_uuid.py \
  --repo-root "$PWD" \
  --private-sft-holds "$ROOT/g1_prior_sft_uuid_owner_policy_v2_private.json" \
  --private-r50-holds "$ROOT/g1_r50_protected_holds_private.json" \
  --private-r57-gold-holds "$ROOT/g1_r57_gold195_source_holds_private.json" \
  --private-output "$ROOT/g1_legacy_dev20_uuid_holds_private.json"
```

请只回传 unittest 结果的简短摘要（运行项数 / PASS 或 FAIL）和最后工具 stdout 的 SAFE JSON；不得回传任何 PRIVATE 文件、原始故事 UUID、完整提示正文、Git Blob 原始内容。

## 判定

- `legacy_dev20_exact_uuid_matches_among_remaining_four > 0`：命中项仅记为继续隔离，不补选、不自动剔除原始固定队列记录。
- `= 0`：仅代表本次确证的两个旧 DEV20 世界没有与剩余 4 条相同 UUID；**不是 G1 全覆盖清关**。
- 无论结果如何：`g1_clearance=HOLD`、`other_protected_uuids_covered=false`、`prior_sft_source_registry_complete=false`、Train/Validation/Teacher = 0。

随后再定位 R56 旧开发目标、其他独立留出集的完整 UUID 来源元数据及历史 Train/Validation/Dev 来源全集，核验覆盖后才考虑 G1 总体状态。禁止语义别名审核、扩样、修改 Skill v0.1、自动付费作业与训练。

## 2026-10-31 Mac 兼容性回归修复

Owner 回报旧 DEV20 实际来源核验 SAFE：旧 Test 的 2 个 UUID / 20 个题目固定来源校验通过，剩余四条与 DEV20 精确命中 0，私有逐条 HOLD 文件已新建，R50 正文访问为 false；这属于 Owner 回报，不是独立复跑。首轮正式 G1 仍 `HOLD`，其他保护世界及历史训练来源完整覆盖仍待核查。

同次 Mac unittest：111 项，110 项成功、`test_14_private_output_no_overwrite_and_0600` 发生 `symlinked private ancestor`。定位为 Darwin 的 `tempfile` 常用 `/var/folders`，其中 `/var` 是系统指向 `/private/var` 的符号链接。修复仅许可 Darwin `/var`→`/private/var`、`/tmp`→`/private/tmp` 且目标严格一致的系统别名，其他任意符号链接继续拒绝；新增两项仅合成测试覆盖非受信祖先与系统别名守卫。

只需在更新分支后重新运行本地测试（原有 111 + 新增 2 = 113），**不要重跑已有真实检查、不要覆盖已创建的私有 `g1_legacy_dev20_uuid_holds_private.json`**。失败时报告测试摘要即可。无新私有数据、无训练准入。
