# StoryForge R58 首轮 G1：R50 保护故事 UUID 交集检查（SAFE）

日期：2026-10-30。本轮冻结 5 条，Owner Mac 已回报 **80/80** 合成测试 PASS，v2 私有隔离清单持久化。R57 27 个历史训练 UUID 中与本批 1 条精确重叠，已在 shortlist 强制排除；剩余 **4 条**需逐一核对保护故事集合。

## 已定位的 R50 保护元数据，不需要人工抄 UUID

GitHub 私有 `sunxu/storyforge` 分支 `audit/r49-r50-source-intake-20261015` 存在且已经远端核实两个固定 **SAFE 元数据回执**：

- `docs/evidence/V03_R50_SOURCE_16_20_RECEIPT_20261015.json`，**Git Blob SHA-1** `2d8623c17ef230d8eff5797a5eb29850e97e6ccb`：含五个 RolePlay 来源故事 `story_id` UUID，来源编号为 16–20；原始来源元数据总计 35 文件。本步仅使用该回执中的 5 个 `story_id` 字段，**不读取来源档案或 R50 测试题**。
- `docs/evidence/V03_R50_46_ADMISSION_STATUS_20261016.json`，Git Blob SHA-1 `20341c6c55bd4564140b05e8319cf66e572137c0`：后续候选数量 46、来源世界数 5、分组键 W16–W20。**此回执是覆盖数量的旁证，不代表 R50 已通过最终 held-out seal**。

R50 的世界 UUID 数据来自冻结的源身份回执，而非助手自造。Owner 已确认 RolePlay 与 R57 同一 UUID 命名空间、每故事 UUID 为独立语义世界。R50 所有五个来源世界均按 Protected 排除范围处理，不因其题目最终评估准入 HOLD 而忽略泄漏风险。

## Mac 一次执行（只读，最多四条比较）

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only

# 只取包含 SAFE 来源回执的 Git 分支对象；不合并、不切换、不提交
git fetch --no-tags origin audit/r49-r50-source-intake-20261015

# 上次总计80项，此次新增8项，预期88项
python3 -m unittest discover -s experiments/r58_round1 \
  -p 'test_*.py' -v &&

ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
python3 experiments/r58_round1/check_r50_protected_uuid.py \
  --repo-root "$PWD" \
  --private-sft-holds "$ROOT/g1_prior_sft_uuid_owner_policy_v2_private.json" \
  --private-output "$ROOT/g1_r50_protected_holds_private.json"
```

`check_r50_protected_uuid.py` 仅以 `git cat-file blob <固定SHA>` 读取**上述两份特定 Git SAFE 回执**；严格验证 five world UUID/16–20、另一回执 46 case/5 source、私有 v2 历史隔离记录 5 条中 1 条已曝光；仅对另外 **4 条**与 R50 五个保护 UUID 做精确比对。

返回的 SAFE JSON 只有计数和是否验证固定元数据 Blob；所有真实 UUID、私有路径留在本机新建 mode 0600 文件（禁止覆盖）。源对象缺失、格式变化、回执与冻结数量不符时退出 HOLD。**不要发送私有 case-level 文件、完整 R50 JSON、原始故事 UUID、原始测试题给助手或上传普通 GitHub。**

### 结果判定

- `r50_exact_uuid_matches_among_remaining_four > 0`：对应故事从后续新独立训练样本候选**排除**（与旧 SFT 曝光相同的严格排除性质），本轮不补选。
- `= 0`：仅证明这 4 个 story UUID 与上述 **五个固定 R50 来源故事** 没有相同 ID。Owner 约定下无需另做跨 UUID 语义世界证明；但仍需核对 **R55/R57 Dev、其他 Protected、历史训练来源覆盖全集**。
- G1 总体仍 `HOLD`，至多四条待审；G2 精确 Runtime Replay、G3 双 Reviewer 暂不启动，Train/Val/Teacher=0，扩样不允许。

## 余下可验证来源

R55/R57 Dev 和其他保护/独立留出集合，不得凭文件名或报告计数臆测“零交集”。下一步只针对这些**实际保护 UUID 集合**查来源及完整性；不再做无关世界图、泛扫描、R50 题目内容和已明确无需的别名评审。

**Owner Mac 的 88 项测试尚未运行；以上是工具准备状态，不是本批 R50 交集结果。** R58 Skill v0.1 未改，PR #7 Draft，首轮完成标记未创建，完成前不触发扩样提醒。
