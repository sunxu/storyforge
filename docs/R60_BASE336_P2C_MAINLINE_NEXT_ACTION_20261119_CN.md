# R60 Base336 — P2-C 主线收敛与 Owner 下一步

## 目标

现在只围绕新的 **8 条 P2 公开来源**完成独立性证明，最终开展 Base 对 Adapter 的质量评估。此前 35 个旧候选案例的冲突预览已完成，不再作为主要工作目标。

现有证据：P2-A 8 来源已 READY；P2 × Base336 172 Story 在已验证范围内 exact Story ID overlap=0；R47/R48/R55 20 个开发题（仅 2 个 Story）精确身份比对 PASS；Reviewer A/B 对旧 Base336 十对边的裁决不是新来源隔离证明。R50 完整 Protected/Reserved 元数据覆盖、完整历史曝光集合、实际历史发送版本和新来源语义审查均未闭合。

## 最小下一步：只检查是否已有 8×172 来源包

仓库已有代码 experiments/r58_quality/r60_base336_p2_source_evidence_capture_cpu.py；**不运行 --execute**，不扩展旧 38 Story 的数据库授权。新工具 experiments/r58_quality/r60_p2c_existing_source_package_preflight_cpu.py 只读取已有 Owner 私有包 R60_BASE336_P2_SOURCE_EVIDENCE_PRIVATE.json 和 R60_P2_PUBLIC_STORY_SOURCE_MANIFEST_PRIVATE.json；校验 336 冻结案例、172 Story/current + archived、8 新来源、来源 Manifest 字节哈希、来源版本和许可标识及精确 Story ID overlap。该检查不是语义审查 PASS。

在 Owner Mac 终端运行以下整段命令（不修改冻结数据、不重查数据库）：

~~~bash
bash <<'BASH'
set -euo pipefail
umask 077
REPO="$HOME/workspace/storyforge-r60-p2-card-opening"
BASE="$HOME/.local/share/storyforge/r60/private"
TOOLS="$BASE/reviewer-tools-git-v2"
BRANCH="docs/r60-p2-r47-r48-r55-source-shape-audit-20261118"
SCRIPT="$TOOLS/r60_p2c_existing_source_package_preflight_cpu.py"
test -d "$REPO" && git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null
test -d "$BASE" && test -d "$TOOLS"
test ! -e "$SCRIPT" && test ! -L "$SCRIPT"
git -C "$REPO" fetch --no-tags origin "$BRANCH"
git -C "$REPO" show FETCH_HEAD:experiments/r58_quality/r60_p2c_existing_source_package_preflight_cpu.py > "$SCRIPT"
chmod 600 "$SCRIPT"
python3 -m py_compile "$SCRIPT"
export BASE SCRIPT
python3 - <<'PY'
import os
import pathlib
import subprocess
import sys
base = pathlib.Path(os.environ['BASE'])
def candidates(name):
    return sorted(p for p in base.rglob(name) if p.is_file() and not p.is_symlink())
packages = candidates('R60_BASE336_P2_SOURCE_EVIDENCE_PRIVATE.json')
manifests = candidates('R60_P2_PUBLIC_STORY_SOURCE_MANIFEST_PRIVATE.json')
if len(packages) != 1 or len(manifests) != 1:
    print({'status': 'P2_8X172_EXISTING_PACKAGE_AVAILABILITY_HOLD',
           'package_matches': len(packages), 'manifest_matches': len(manifests),
           'database_accessed': False, 'p2_c': 'HOLD'})
    sys.exit(42)
sys.exit(subprocess.call([sys.executable, os.environ['SCRIPT'],
                          '--package', str(packages[0]),
                          '--p2-manifest', str(manifests[0])]))
PY
BASH
~~~

若出现 P2_8X172_EXISTING_PACKAGE_AVAILABILITY_HOLD、package_matches=0，说明目前不能使用完整 8×172 私有包。**不得**用之前 38 Story 的私有证据替代，亦不得因该结果自动重查数据库。需先查已有获批快照是否包含该包；如确实缺失，单独申请限定的只读 172 Story 来源捕获授权。

若出现 P2_8X172_SOURCE_PACKAGE_STRUCTURALLY_READY__SEMANTIC_CROSSWALK_HOLD，说明可以复用该完整包，下一步是 8 P2 来源与 172 Base336 历史版本的世界/角色/开场的人工或隔离 Reviewer 语义比对。工具只会输出 SAFE 聚合，不会输出 Story ID、正文、私有路径或 SHA。

## 其他并行门禁（不重复已通过的子项）

1. R50 完整 Protected/Reserved **metadata-only** 清单的来源与覆盖闭合，不打开 R50 密封正文。
2. R47/R48/R55 已暴露范围的全历史集合闭合，保留已完成的 20-case/2-Story 精确 ID 核验，不重复该动作。
3. Historical actual-sent 版本与来源绑定，不能以 current/archived 可用代替实际发送证明。
4. 8 条新来源的独立 Reviewer 审查和 Owner 冻结；若个别来源无法证明独立，维持 HOLD 或替换，而不是强行 PASS。
5. P2-C 全通过之后，再构造、复核并冻结 8×6=48 条真实评估提示，进入 P3–P6；GPU 推理仍需单独授权。

固定状态：P2_C=HOLD；P2_B_48_PROMPTS=NOT_GENERATED；train_admitted=0；quality_v1_admitted=0；model_promoted=false。

## 2026-11-19 Owner 真实运行结果：完整来源包缺失

Owner 实际执行新增的无数据库预检后返回：

```text
status = P2_8X172_EXISTING_PACKAGE_AVAILABILITY_HOLD
package_matches = 0
manifest_matches = 1
database_accessed = false
p2_c = HOLD
```

这是**真实文件可用性回执**：在 Owner 本次扫描的私有根目录里，唯一的 8 条 P2 Source Manifest 存在；但没有预期文件名的完整 `R60_BASE336_P2_SOURCE_EVIDENCE_PRIVATE.json`。不能声称其他名字的快照绝对不存在，不能把已有 38 Story / 59 条记录的旧证据包装为全 172 Story，也不要重复运行同一个搜索/预检。

继续优先推进 P2 新来源隔离。仓库已存在 `experiments/r58_quality/r60_base336_p2_source_evidence_capture_cpu.py`：其默认（**不加** `--execute`）路径只验证既有六组冻结目录、完整 336/172 来源身份，以及 8 条 P2 Manifest；返回 `P2_BASE336_SOURCE_EVIDENCE_PRECHECK__NO_DB` 时，仍没有读取数据库或创建来源正文包。

若离线预检通过，而其他经核对的既有快照仍不具备 172 Story current + all archived 的完整 World/Character/Opening 字段，则需明确的 **Owner 最小范围只读数据库捕获授权**，不能沿用先前 38 Story 的数据库读取许可，不能把“运行预检”解读为授权执行捕获。授权范围应仅为：冻结 172 个 Story 的 `world/character/characters/opening` current+archived，以及已批准 8 条 P2 public snapshot 的 revision/moderation/permission 字段；RLS 只读角色，`REPEATABLE READ READ ONLY`，仅 Owner Mac 私有 create-only 0700/0600 输出，SAFE 聚合回执。不得查询 R50 密封正文、用户私有会话消息、训练/推理/API、扩大数据集或修改数据库。

后续批准后执行仍属于**来源证据收集**，不是 P2-C PASS。之后必须开展 P2×Base336 语义比较、R50 完整 Protected/Reserved metadata-only 覆盖、旧曝光全集、历史 actual-sent 版本绑定、独立复核与 Owner Freeze。P2-C 与 48 提示继续 HOLD/NOT_GENERATED。


## Owner Mac 无数据库预检：已知六个冻结目录的精确命令

已从既有 R60 Owner 冻结审计流程恢复六个**已使用过的目录名称**，不是新构造的目录。此命令只执行仓库已经存在的捕获器的默认预检，**故意不传 \`--execute\`**，不打开数据库、不会生成任何私有来源正文包。

~~~bash
bash <<'BASH'
set -euo pipefail
umask 077
REPO="$HOME/workspace/storyforge-r60-p2-card-opening"
BASE="$HOME/.local/share/storyforge/r60/private"
TOOLS="$BASE/reviewer-tools-git-v2"
BRANCH="docs/r60-p2-r47-r48-r55-source-shape-audit-20261118"
SCRIPT="$TOOLS/r60_base336_p2_source_evidence_capture_cpu.py"
P2_MANIFEST="$BASE/r60-p2-public-source-inventory-20261118/R60_P2_PUBLIC_STORY_SOURCE_MANIFEST_PRIVATE.json"
OUTPUT="$BASE/r60-base336-p2-full-source-evidence-20261119-v1"

test -d "$REPO" && test -d "$TOOLS"
test -f "$P2_MANIFEST"
test ! -e "$OUTPUT" && test ! -L "$OUTPUT"
test ! -e "$SCRIPT" && test ! -L "$SCRIPT"

git -C "$REPO" fetch --no-tags origin "$BRANCH"
git -C "$REPO" show \
  FETCH_HEAD:experiments/r58_quality/r60_base336_p2_source_evidence_capture_cpu.py \
  > "$SCRIPT"
chmod 600 "$SCRIPT"

export PYTHONPATH="$REPO/src:$REPO/experiments/r58_quality:$TOOLS"

python3 "$SCRIPT" \
  --old-dir "$BASE/r60-quality-fast1000-api-v1" \
  --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114" \
  --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1" \
  --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1" \
  --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1" \
  --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1" \
  --p2-manifest "$P2_MANIFEST" \
  --output-dir "$OUTPUT"
BASH
~~~

预期成功 SAFE：\`status=P2_BASE336_SOURCE_EVIDENCE_PRECHECK__NO_DB\`、336 cases、172 unique stories、8 public P2 sources、P2 exact Story ID overlap=0、\`database_accessed=false\`、\`private_file_created=false\`。如返回 HOLD，仅发送 SAFE 的 status/reason_code/计数，不发送私有路径、哈希或数据内容。

后续如需传 \`--execute\`，必须单独获得 Owner 对 172 Story current+全部归档 World/Character/Opening、8 P2 approved public snapshot 的**明确最小范围只读数据库授权**。该目录及源对象不得覆盖或自动重试。没有授权时止于预检。


## 2026-11-19 Owner 无数据库预检通过（当前最新状态）

Owner 已提供完整 SAFE JSON（已提交到 `docs/evidence/R60_BASE336_P2_FULL_SOURCE_PRECHECK_SAFE_20261119.json`），结果：

```text
status = P2_BASE336_SOURCE_EVIDENCE_PRECHECK__NO_DB
base336_cases = 336
base336_story_ids = 172
p2_sources = 8
p2_base336_exact_story_id_overlap = 0
private_file_created = false
database_accessed = false
database_modified = false
train_admitted = 0
```

先前 `package_matches=0, manifest_matches=1` 与本次成功预检**不矛盾**：前者表示完整 8×172 原文来源包尚未在 Owner 私有目录中找到；后者表示使用已存在的冻结身份/授权 Manifest，离线运行捕获器能够验证本次限定范围与输出前置条件，**没有生成或读取全量 World/Character/Opening 来源正文**。

**状态：OFFLINE_CAPTURE_PRECHECK_COMPLETE，FULL_SOURCE_PACKAGE_MISSING，DB_CAPTURE_NOT_AUTHORIZED；P2_C=HOLD。** 不要重跑同一预检或旧八组/35 案例审查。接下来若 Owner 明确批准，才能在 Owner Mac 使用既有 `r60_base336_p2_source_evidence_capture_cpu.py --execute` 执行一次范围严格受限的只读捕获（冻结 172 Story current+archived 四类字段、8 P2 已批准 public snapshot + 版本/权限绑定）。捕获器内部使用现成 RLS 预检与 `REPEATABLE READ READ ONLY`，无数据库写入；要求 private 0700/0600 create-only，输出只允许回传 SAFE JSON。不查询 R50 密封正文、不查询私有聊天消息、不扩大素材范围。

执行前检查：
- 明确 Owner 对这次 **172 Story + 8 P2** 只读数据库访问的授权（之前 38 Story 授权不自动覆盖）；
- `R60_READONLY_DATABASE_URL` 在 Owner 本机已正确设置（只检查是否存在，不向日志输出）；
- 已预检的六个冻结来源目录、P2 Manifest 和输出目标未变；目标目录必须不存在；
- 公开脚本版本已固定，禁止为了绕过失败擅自修改 SQL、RLS 或权限控制。

拿到捕获器 SAFE `P2_BASE336_SOURCE_EVIDENCE_CAPTURED__SEMANTIC_REVIEW_REQUIRED` 后，也仅关闭**来源证据采集**，不能升级为 P2-C PASS。仍需对 8 来源与 Base336 全 172 Story 的 current+historical 实质字段做来源绑定语义交叉核验、R50 完整 Protected/Reserved metadata-only 排除、R47/R48/R55 曝光全集闭合、actual-sent、独立 Reviewer 与 Owner Freeze。48 条正式提示仍 NOT_GENERATED。
