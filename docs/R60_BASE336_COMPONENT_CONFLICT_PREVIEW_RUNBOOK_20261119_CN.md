# R60 Base336：组件冲突候选图 Owner 离线执行说明（2026-11-19）

## 目标和边界

无需等待 Reviewer B 的独立性资格认证，即可执行 **只读的隔离风险预览**。工具将 V2 候选包中十条跨 Train/Validation 边**假设**为同一语义组件，用仓库已有的 world_isolation.component_split_conflicts 检测跨拆分连通分量。该假设不是 Reviewer 的正式、逐边、可认证裁决；其余 16 条同拆分候选边不自动合并，未命中的 Story 不构成隔离 PASS。

以 Owner 已上传的实际八组 Card/Opening、冻结 roster 和 V2 packet 实测：10 条跨拆分边形成 **6 个候选冲突组件**，组件大小 **2、2、2、2、3、5**；总计 **16 个不同 Story / 35 个去重候选案例**。仍有 22 个 Story 不在这些跨拆分边内，但其独立性并未证明。

**所有 P2-C、R50 完整排除、实际历史发送版本、Reviewer 独立性、Owner Freeze 门禁仍是 HOLD。** 本工具不读取数据库、不训练、不生成 48 prompts、不修改冻结拆分、不访问 R50 正文。

## Mac 一次执行：只读输入、私有 create-only 输出

以下命令要求本机存在原有 StoryForge Git 工作区、八组 Card/Opening 和 V2 私有候选包。只从 GitHub 获取新加入的公开脚本，不需要重新下载原始文件。

\`\`\`bash
bash <<'BASH'
set -euo pipefail
umask 077

REPO="$HOME/workspace/storyforge-r60-p2-card-opening"
BASE="$HOME/.local/share/storyforge/r60/private"
TOOLS="$BASE/reviewer-tools-git-v2"
GROUPS="$BASE/r60-base336-group-cards-opening-20261115"
PACKET="$BASE/R60_BASE336_COMPONENT_REVIEW_PACKET_PRIVATE_V2_20261119.json"
OUT="$BASE/r60-base336-component-conflict-preview-20261119-v1"
BRANCH="docs/r60-p2-r47-r48-r55-source-shape-audit-20261118"

test -d "$REPO" && git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null
test -d "$BASE" && test -d "$TOOLS" && test -d "$GROUPS" && test -f "$PACKET"
test -f "$TOOLS/r60_independent_reviewer_offline.py"
test ! -e "$TOOLS/r60_base336_component_conflict_preview_cpu.py"
test ! -L "$TOOLS/r60_base336_component_conflict_preview_cpu.py"
test ! -e "$OUT" && test ! -L "$OUT"

ROSTER_COUNT="$(find "$BASE" -type f -name 'R60_BASE336_WORLD_CROSS_SPLIT_REVIEW_PRIVATE.json' | wc -l | tr -d ' ')"
if [ "$ROSTER_COUNT" -ne 1 ]; then
  echo "ROSTER_COUNT_HOLD=$ROSTER_COUNT"
  exit 42
fi
ROSTER="$(find "$BASE" -type f -name 'R60_BASE336_WORLD_CROSS_SPLIT_REVIEW_PRIVATE.json' -print -quit)"

git -C "$REPO" fetch --no-tags origin "$BRANCH"
git -C "$REPO" show FETCH_HEAD:experiments/r58_quality/r60_base336_component_conflict_preview_cpu.py \
  > "$TOOLS/r60_base336_component_conflict_preview_cpu.py"
chmod 600 "$TOOLS/r60_base336_component_conflict_preview_cpu.py"

# 复用既有 world_isolation 模块，不复制隔离判定算法。
export PYTHONPATH="$REPO/src:$TOOLS"
python3 "$TOOLS/r60_base336_component_conflict_preview_cpu.py" \
  --packet "$PACKET" \
  --roster "$ROSTER" \
  --inputs "$GROUPS" \
  --output-dir "$OUT"

echo "COMPONENT_PREVIEW_PREPARED"
BASH
\`\`\`

正常 SAFE stdout：status=BASE336_COMPONENT_CONFLICT_PREVIEW_READY__P2_C_HOLD、candidate_cross_split_edges=10、candidate_cross_split_components=6、candidate_affected_stories=16、candidate_affected_cases=35、p2_c=HOLD、train_admitted=0。

私有目录权限 0700，两个 create-only 文件均为 0600：
- R60_BASE336_COMPONENT_CONFLICT_PREVIEW_PRIVATE.json：源 Story/拆分/案例位置和候选组件的私有对应，仅 Owner 可访问。
- R60_BASE336_COMPONENT_CONFLICT_PREVIEW_SAFE.json：无私有 ID、正文、SHA，可回传此对话。

可选参数：--reviewer-b-safe PATH 可以读取原有 B 的 SAFE 聚合回执，核实其 10/10 结构统计，但不会升级 reviewer_b_independence_verified，也不证明逐边裁决内容。省略也可以生成预览。

已有输出目录 -> OUTPUT_EXISTS_HOLD。来源 SHA、roster、版本记录、split 不一致 -> 固定 HOLD，**不删除、不覆盖、不更换目录规避检查**。

## 2026-11-19 实际运行故障修复：`--inputs 20`

Owner 终端曾运行 `--inputs 20`，得到 `{"status":"HOLD","reason_code":"UNEXPECTED_HOLD",...}`。**根因有两层**：

1. `--inputs` 是目录型参数，必须传 **8 份原始 `R60_BASE336_WORLD_GROUP_XX_CARD_OPENING_PRIVATE.json` 所在目录**；不能传数量 `20`。数字 20 是本轮 Reviewer 的证据/裁决文件数量，与此输入参数无关。
2. 原版组件工具定义自己的 `Hold`，而证据检查器使用 `r60_independent_reviewer_offline.Hold`，导致被复用模块的安全原因码误报告为 `UNEXPECTED_HOLD`。现已统一共享 `Hold`，新增目录类型检查，错误用 `INPUTS_DIRECTORY_HOLD` 直接报告而不泄露私有数据；新加合成测试验证无输出目录创建及共享异常原因的保留。

必须先从 GitHub 获取更新后的 `experiments/r58_quality/r60_base336_component_conflict_preview_cpu.py`，替换**已有本地旧脚本时需保留旧副本并先核对差异**。此次参数修正后的完整示例：

```bash
set -euo pipefail
umask 077
REPO="$HOME/workspace/storyforge-r60-p2-card-opening"
BASE="$HOME/.local/share/storyforge/r60/private"
TOOLS="$BASE/reviewer-tools-git-v2"
INPUT="$BASE/r60-base336-group-cards-opening-20261115"
ROSTER="$BASE/r60-base336-world-cross-review-20261115/R60_BASE336_WORLD_CROSS_SPLIT_REVIEW_PRIVATE.json"
PACKET="$BASE/R60_BASE336_COMPONENT_REVIEW_PACKET_PRIVATE_V2_20261119.json"
OUT="$BASE/r60-base336-component-conflict-preview-20261119-v1"
test -d "$INPUT"
test -f "$ROSTER" && test -f "$PACKET"
test ! -e "$OUT" && test ! -L "$OUT"
export PYTHONPATH="$REPO/src:$TOOLS"
python3 "$TOOLS/r60_base336_component_conflict_preview_cpu.py" \
  --packet "$PACKET" \
  --roster "$ROSTER" \
  --inputs "$INPUT" \
  --output-dir "$OUT"
```

此处 `INPUT` 路径以 Owner 原有目录存在为前提，切勿自动生成空源目录。若之前错误运行创建了输出目录，则先做证据保全与人工核验，不允许简单删除或覆盖。同样不应为了绕开 HOLD 而重建证据或更换文件来源。

## 后续使用

1. 将这 6 个组件的 35 条候选案例在 Owner 私有工作流中标记为临时隔离观察对象（**不修改冻结 split、数据库或源文件**）。
2. 等待正式逐边裁决后修改**新的、版本化的组件映射提案**，不得覆盖本轮预览。
3. 对覆盖完整 Story 的源绑定组件分配调用已存在的 validate_component_review_assignments；不能把结构 PASS 冒充完整语义隔离、Reviewer 独立性或训练准入。
4. 实际历史发送版本、R50 完整 metadata-only 保护名单、R47/R48/R55 全量历史曝光可以并行继续核对，不应被 B 资格核验阻塞。

固定状态：P2_C=HOLD；P2_B_48_PROMPTS=NOT_GENERATED；train_admitted=0；quality_v1_admitted=0。
