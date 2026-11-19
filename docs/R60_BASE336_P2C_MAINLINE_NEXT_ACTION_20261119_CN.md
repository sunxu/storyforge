# R60 Base336 — P2-C 主线收敛与 Owner 下一步

## 下一项直接核验：冻结 R50 五世界 UUID ↔ 原始 50 来源 ↔ P2 八来源

**新找到的权威 metadata-only 原件**（无需 R58 五范围空白 CSV）：

- Git SHA `2d8623c17ef230d8eff5797a5eb29850e97e6ccb`：R50 已冻结源身份 SAFE，5 个唯一故事 UUID、5 个唯一 Session、W16–W20、35 个历史来源文件条目，源 Commit 固定为 `a197923e1e15344e8c98bd96e593e84781b68c83`。
- Git SHA `20341c6c55bd4564140b05e8319cf66e572137c0`：R50 46 候选、5 来源世界、4 排除，W16–W20 五组。
- 已用 GitHub 连接**直接读取两份固定 SAFE Blob 的结构与统计**，结果记于 `docs/evidence/R60_P2_R50_PINNED_FIVE_WORLD_METADATA_SOURCE_SAFE_20261119.json`。没有读取保护集的原始故事正文、提示、答案或密封题目；当前只是 Git 源身份 receipt 级证据，不是本地 50 条 provenance UUID 集合的实际同一性核验。

已有函数 `experiments/r58_round1/check_r50_protected_uuid.py::blob_json/protected_ids` 严格验证以上两个历史 Git SAFE Blob 并返回五个 R50 story UUID；`scripts/r60_r50_original50_complement_cpu.py::jsonl` 验证原 50 条 **provenance-only** 固定 SHA；`scripts/r60_r50_freeze_status_projection_cpu.py::read_private_json` 安全读取已批准的八来源 P2 Manifest。**不开发新审计脚本**，只在 Owner Mac 对这三个现成集合做精确身份等价/交集检查。

```bash
bash <<'BASH'
set -euo pipefail
set +x
umask 077
REPO="$HOME/workspace/storyforge-r60-p2-card-opening"
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
R50="$HOME/.local/share/storyforge/r50/original-frozen-20261016/R50_CASE_PROVENANCE_50.jsonl"
P2="$HOME/.local/share/storyforge/r60/private/r60-p2-public-source-inventory-20261118/R60_P2_PUBLIC_STORY_SOURCE_MANIFEST_PRIVATE.json"
test -x "$PY" && test -f "$R50" && test -f "$P2"
test -d "$REPO/.git" || test -f "$REPO/.git"
# 取既有审计分支的固定 SAFE Git Blob；不切换工作树或读取故事源档案
git -C "$REPO" fetch --no-tags origin audit/r49-r50-source-intake-20261015
export PYTHONPATH="$REPO"
export REPO R50 P2
"$PY" - <<'PY'
import json
import os
from pathlib import Path

from experiments.r58_round1.check_r50_protected_uuid import (
    SOURCE_SHA, COVERAGE_SHA, UUID, blob_json, protected_ids,
)
from scripts.r60_r50_original50_complement_cpu import jsonl
from scripts.r60_r50_freeze_status_projection_cpu import read_private_json

report = {
    "schema": "storyforge_r60_p2_r50_pinned5_to_provenance_binding_safe_v1",
    "status": "R50_PINNED_FIVE_IDENTITY_BINDING_HOLD",
    "failure_phase": "SOURCE_BLOB",
    "pinned_five_worlds_verified": False,
    "r50_original_50_provenance_verified": False,
    "r50_pinned_five_equals_original50_source_set": False,
    "p2_public_sources_checked": 0,
    "p2_pinned_r50_story_id_overlap": None,
    "all_other_protected_reserved_sources_verified": False,
    "r50_sealed_content_read": False,
    "database_accessed": False,
    "private_values_emitted": False,
    "p2_c": "HOLD",
    "train_admitted": 0,
}
try:
    repo = Path(os.environ["REPO"])
    src = blob_json(repo, SOURCE_SHA)
    admission = blob_json(repo, COVERAGE_SHA)
    protected = protected_ids(src, admission)
    report["pinned_five_worlds_verified"] = len(protected) == 5
    report["failure_phase"] = "R50_PROVENANCE_SOURCE_SET"
    original = jsonl(Path(os.environ["R50"]), 50, "provenance")
    values = [row.get("source_story_id") for row in original]
    if not all(isinstance(v, str) and UUID.fullmatch(v) for v in values):
        raise ValueError("source_id_invalid")
    original_ids = {v.lower() for v in values}
    if len(original_ids) != 5 or original_ids != protected:
        raise ValueError("source_set_mismatch")
    report["r50_original_50_provenance_verified"] = True
    report["r50_pinned_five_equals_original50_source_set"] = True

    report["failure_phase"] = "P2_MANIFEST_EXACT_STORY"
    manifest = read_private_json(Path(os.environ["P2"]))
    if manifest.get("schema") != "storyforge_r60_base336_p2_public_source_inventory_private_v1":
        raise ValueError("p2_schema_mismatch")
    rows = manifest.get("sources")
    if not isinstance(rows, list) or len(rows) != 8:
        raise ValueError("p2_count_mismatch")
    ids = [row.get("story_id") for row in rows]
    if not all(isinstance(v, str) and bool(v) for v in ids):
        raise ValueError("p2_source_invalid")
    p2_ids = {v.lower() for v in ids}
    if len(p2_ids) != 8:
        raise ValueError("p2_duplicate_source")
    overlap = len(p2_ids & protected)
    report["p2_public_sources_checked"] = 8
    report["p2_pinned_r50_story_id_overlap"] = overlap
    if overlap != 0:
        raise ValueError("p2_protected_overlap")
    report["status"] = "R50_PINNED_FIVE_BOUND_TO_ORIGINAL50__P2_EXACT_DISJOINT__UNIVERSE_HOLD"
    report["failure_phase"] = "COMPLETE"
except Exception:
    report["reason_code"] = report["failure_phase"] + "_HOLD"
print(json.dumps(report, sort_keys=True))
raise SystemExit(0 if report["failure_phase"] == "COMPLETE" else 42)
PY
BASH
```

此命令**不会运行原 50 case JSONL 的 sealed content**，也不读取历史来源档案正文，仅在 Owner Mac 内比对元数据 UUID；stdout 不含 Story UUID、路径、哈希或任何来源原文。返回 SAFE 即可；失败只显示固定 phase，不打印异常或私有值。

**能关闭的门禁：** 冻结的五个 R50 保护世界源身份集合是否等于原 50 条 provenance 的全部 Story ID，以及 P2 是否与这五个固定世界精确不重叠。**仍不能关闭：** R50 外其它 Protected/Reserved 全集、五世界之外的隐藏语义组件、Base336 172 Story 全版本隔离、历史实际送达和正式 Owner freeze。P2-C 继续 HOLD，48 真实提示不得生成。

---


## 最新 Owner 结果：R58 五范围索引为空，停止沿该路径重复盘点（2026-11-19）

Owner 实际执行历史 `experiments/r58_round1/audit_g1_index_readiness.py` 并返回 `R58_G1_SOURCE_EXISTENCE_PREFLIGHT_ONLY__WORLD_AND_PROTECTION_HOLD`。原始回执存于 `docs/evidence/R60_P2C_R58_G1_EMPTY_SOURCE_REFERENCES_OWNER_SAFE_20261119.json`。

- `scope_count=5`，五行全部 `MISSING_SOURCE_REFERENCE`；`source_files_present_unopened=0`、`owner_coverage_claims_present=0`、`independently_verified_complete_scopes=0`。
- `source_index_bytes_read=false`、`protected_test_content_read=false`、`candidate_story_content_read=false`；该检查**没有打开任何被引用的权威来源文件**。
- **精确解释**：这只证明 R58 旧五行 CSV **未绑定任何来源引用**，不是“R50 / SFT / R55 等原始材料不存在”。既有 R50 原 50 条 provenance、R50 World Inventory、R47/R48/R55 20-case 等其它来源文件仍按各自独立已核验证据处理。
- **停止动作**：不重跑这份 CSV、不要填假 `OWNER_COVERAGE_ATTESTED`、不制造新的 R58 索引；本旧工具并不负责 R60 新 8 来源全集门禁。它的 `g1_clearance=HOLD` 也不是 R60 任务的新 FAIL。

**主线接力：**
1. R50 原始 50 条 provenance = 46+4 及 P2 exact Story ID overlap=0 **继续 PASS，不重复跑**。已知 5 个 R50 原始来源世界属有限来源范围；完整 Protected/Reserved **权威**名单的来源版本/穷尽性与隐藏别名均未提供，不得凭旧 R58 空表也不得凭 World Inventory 的存在性直接推断 PASS。
2. R47/R48/R55 旧 20 Prompt（2 Story）的 SHA/复合身份/索引传递链 **继续 PASS，不重跑**。仅继续寻找**其它**历史开发、仲裁、训练和保留来源权威清单，不用相同 20 个 Prompt 反复充数。
3. Base336 × P2 新 8 来源仍需全 172 Story current+archived 世界/卡/开场语义核验，Owner 捕获器上次停在 `DB_BASE336_SOURCE_QUERY_HOLD`，没有根因证据之前不重复 SQL。
4. `historical_actual_sent_verified=false`、独立 Reviewer 和 Owner Freeze HOLD。保持所有私有原文、密封内容及数据库凭据不进入公共 GitHub。

**下一步不再使用 R58 空白 CSV。** 只对已知存在的 `R50_FULL_ORIGINAL_WORLD_INVENTORY_PRIVATE.json` 及历史来源原始授权/封存来源文档做元数据范围证明：应有能够绑定原始 50 条 provenance 来源的受信标识、对应的冻结版本，以及“Protected/Reserved 不再存在未列来源”的权威边界文件；无法取得则如实单独 HOLD。不要为了消除 HOLD 而重新生成或改变历史文件。

`P2_C=HOLD`、`P2_B_48_PROMPTS=NOT_GENERATED`、`train_admitted=0`、`model_promoted=false` 不变。

---


## 最新状态：R50 provenance 与历史曝光已知范围（2026-11-19）

**当前动作优先级高于下文所有旧的捕获器/数据库重试步骤。** P2-C 仍围绕 **新 8 条公开评估来源的独立性**，不扩展旧 35 案例审计。

| 子门禁 | 可复用的已验证 SAFE | 仍 HOLD 的唯一缺口 |
|---|---|---|
| R50 原始 50 来源 | Owner 实际回执 `R50_PROVENANCE_50_46_4_METADATA_PASS__P2_C_HOLD`：50 原始来源 provenance = 46 派生 + 4 排除；P2 对这 50 条来源 Story ID 精确 overlap=0，且 R50 密封题目未打开。回执 `docs/evidence/R60_P2_R50_50_46_4_PROVENANCE_COMPLEMENT_SAFE_20261119.json` | R50 Protected/Reserved **世界/语义组件权威完整元数据 roster** 与最终封存证据；原 50 cases 的冻结字节未在本轮重新开启或验证 |
| Base336 | Owner P2×172 离线预检 PASS，旧 8 组 38 Story/59 来源版本已审，候选组件预览 6 个；P2 exact Story ID overlap=0 | P2 对全部 172 Story 当前与归档语义字段；此前 DB_BASE336_SOURCE_QUERY_HOLD，不能凭 EXPLAIN 假设 Owner 查询可执行 |
| R47/R48/R55 已知旧开发链 | 20 Prompt 对应 **2 Story**，同一 R47/R48/R55 继承链；P2 exact overlap=0；R55 三层 76/68/46 索引及 20/20 来源绑定已 PASS | **完整历史已曝光全集**、其他开发/仲裁来源及语义别名，不能把已知 20 题当作全集 |
| actual-sent、独立 Review、Owner Freeze | 现有局部静态索引可复用 | 均 HOLD |

**发现可复用的更早来源全集缺口清单。** `docs/evidence/R58_G1_R55_R56_R57_PROTECTED_SOURCE_GAP_MATRIX_SAFE_20261101.json` 已从历史冻结 GitHub 证据列出五类已知部分来源（`known_historical_sft` / `r50_known_protected` / `gold195_source` / `legacy_dev20` / `r04_non_gold`），同时明确 **三类尚未取得权威完整名单**：`r55_r57_other_dev`、`other_reserved_heldout`、`other_historical_training`。R58 的候选集合与 R60 新 P2 不是同一个集合，因此旧结论只能继承**来源全集仍有缺口的证据**，不能继承为 R60 交集核验 PASS。

**R50 Inventory 保留独立证据边界。** Owner 既有 `r50/full-original-worlds/run.cGUPnjdx/R50_FULL_ORIGINAL_WORLD_INVENTORY_PRIVATE.json` 文件（历史 metadata inventory 见 0600 / 10061 bytes）；现有字段类型投影和文件存在性不足以证明它是完整 Protected/Reserved 的来源权威 roster，也不能据此确认隐藏 World alias 语义隔离。不得为了凑覆盖数读取 R50 密封题目。

**下一项只读、无重复开发的 Owner 本地动作**：仅检查旧 R58 五范围现存来源元数据 CSV 对权威索引的引用就绪情况，复用 `experiments/r58_round1/audit_g1_index_readiness.py`；它只读五行本地元数据 CSV、`lstat` 其引用文件，**不读取引用的保护集合正文/索引**。如 CSV 不存在，一次报告缺失并停止，不重新生成、不要填充假数据或虚构 OWNER_COMPLETE。

```bash
bash <<'BASH'
set -euo pipefail
set +x
REPO="$HOME/workspace/storyforge-r60-p2-card-opening"
ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
INV="$ROOT/g1_evidence_inventory_private.csv"
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
test -x "$PY" && test -f "$REPO/experiments/r58_round1/audit_g1_index_readiness.py"
if [ -f "$INV" ] && [ ! -L "$INV" ]; then
  "$PY" "$REPO/experiments/r58_round1/audit_g1_index_readiness.py" --private-inventory "$INV"
else
  printf '%s\n' '{"schema":"r60_p2c_existing_scope_inventory_availability_safe_v1","status":"EXISTING_OWNER_PRIVATE_SCOPE_INVENTORY_NOT_FOUND__P2_C_HOLD","source_index_bytes_read":false,"protected_content_read":false,"database_accessed":false,"p2_c":"HOLD","train_admitted":0}'
fi
BASH
```

这项检查**只回答旧已知权威来源索引是否就绪**，不认证 R50 完整保护集、不新增 P2 语义裁决，也不将 R58 的五候选合同套用到 R60。返回非零/缺失均停止该检查，进入其他独立工作，不反复扫描。

永久保持 `P2_C=HOLD`、`P2_B_48_PROMPTS=NOT_GENERATED`、`train_admitted=0`。避免重复运行 R50 50/46/4、R47/R48/R55 20-case、旧 35 案例候选图以及无新错误依据的 Base336 捕获 SQL。

---


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


## 2026-11-19 Owner 已授权限定只读来源捕获

Owner 在本对话明确授权本次来源捕获，并指示**后续同一 StoryForge 主线的数据库访问无需逐次另行申请**。这是对只读验证的执行许可，不会取消既有 RLS / read-only / 私有证据 / R50 密封 / 数据完整性 / GPU / 训练等门禁；未经任务授权不得写库、访问 R50 密封正文或读取私有聊天内容。必须保持精确的冻结 ID 过滤条件、最小字段范围与 SAFE 聚合输出。

本次已有成功离线回执 `P2_BASE336_SOURCE_EVIDENCE_PRECHECK__NO_DB`：336 案例、172 个来源 Story、8 条 P2 公开来源、exact Story ID overlap 0。完整 8×172 来源包仍缺失，现可在**Owner Mac** 原有 read-only DB 连接下，对已验证的相同六个冻结目录和 8 条 P2 Manifest 执行 **一次** `--execute`。由于这些冻结 ID 和私有凭据只在 Owner 本机，GitHub/CI 不运行数据库捕获，也不在此对话传输源码/私有原文。

严格执行命令（脚本沿用通过预检的那一份；保护输出目录不被覆盖）：

```bash
bash <<'BASH'
set -euo pipefail
set +x
umask 077
REPO="$HOME/workspace/storyforge-r60-p2-card-opening"
BASE="$HOME/.local/share/storyforge/r60/private"
TOOLS="$BASE/reviewer-tools-git-v2"
SCRIPT="$TOOLS/r60_base336_p2_source_evidence_capture_cpu.py"
MANIFEST="$BASE/r60-p2-public-source-inventory-20261118/R60_P2_PUBLIC_STORY_SOURCE_MANIFEST_PRIVATE.json"
OUT="$BASE/r60-base336-p2-full-source-evidence-20261119-v1"

test -f "$SCRIPT" && test -f "$MANIFEST"
test -d "$BASE" && test ! -e "$OUT" && test ! -L "$OUT"
if [ -z "${R60_READONLY_DATABASE_URL:-}" ]; then
  echo "DB_DSN_HOLD: R60_READONLY_DATABASE_URL is not set in this shell"
  exit 42
fi

git -C "$REPO" fetch --no-tags origin docs/r60-p2-r47-r48-r55-source-shape-audit-20261118
cmp -s "$SCRIPT" <(git -C "$REPO" show FETCH_HEAD:experiments/r58_quality/r60_base336_p2_source_evidence_capture_cpu.py) || {
  echo "SCRIPT_VERSION_HOLD: local script differs from the reviewed GitHub version"
  exit 42
}
export PYTHONPATH="$REPO/src:$REPO/experiments/r58_quality:$TOOLS"
python3 "$SCRIPT" \
  --old-dir "$BASE/r60-quality-fast1000-api-v1" \
  --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114" \
  --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1" \
  --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1" \
  --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1" \
  --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1" \
  --p2-manifest "$MANIFEST" \
  --output-dir "$OUT" \
  --execute
BASH
```

只有 `P2_BASE336_SOURCE_EVIDENCE_CAPTURED__SEMANTIC_REVIEW_REQUIRED` 才表示完成本次字段来源捕获且仍需语义审查。若出现 `P2_BASE336_SOURCE_EVIDENCE_HOLD`，保持失败关闭，**不得删除或覆盖部分生成的私有目录，不得绕过 RLS 或改变冻结 ID 清单**。只回传完整的 SAFE JSON，不回传任何数据库 URL、Story ID、源值、逐项对照、路径或 SHA。

后续严格沿主线先完成新 8 来源对 Base336 172 Story 的语义排除，再推进 R50 完整 metadata-only 保护集闭合、R47/R48/R55 全历史曝光闭合、actual-sent 版本绑定、独立 Reviewer/Owner Freeze；P2-C 继续 HOLD，P2-B 48 prompts 仍 NOT_GENERATED，train_admitted=0。


## 2026-11-19 捕获运行时 HOLD：先查 psycopg，再用分阶段 SAFE 诊断

Owner 本轮使用 `--execute` 后返回：

```text
status = P2_BASE336_SOURCE_EVIDENCE_HOLD
reason_code = SOURCE_CAPTURE_OR_RUNTIME_HOLD
database_accessed = null
private_file_created = false
```

**不等于已定位数据库驱动问题**：原版工具的泛化异常处理会将 `psycopg` 导入失败、数据库连接失败、SQL 错误、只读/RLS 保护拒绝，以及查询后本地数据处理异常归并为相同 code。`database_accessed=null` 仅表示失败路径未记录访问是否完成。

已在同一公开捕获器中修复 SAFE 诊断，保持源捕获 SQL、RLS、冻结范围、输出防覆盖及 P2-C HOLD 不变；新增分阶段失败标记 `failure_phase` 和固定原因：
- `DB_DRIVER_IMPORT_HOLD`：本次运行的 Python 无法导入 `psycopg`（项目使用 psycopg3，不是 psycopg2）。
- `DB_DRIVER_RUNTIME_HOLD`：连接阶段 Python 驱动原生依赖不可用。
- `DB_CONNECTION_HOLD`：连接/认证/TLS/网络失败（不披露原始错误）。
- `DB_TRANSACTION_SETUP_HOLD` / `DB_ROLE_RLS_PREFLIGHT_HOLD`：只读事务、角色/RLS 预检。
- `DB_BASE336_SOURCE_QUERY_HOLD` / `DB_P2_PUBLIC_SOURCE_QUERY_HOLD`：某个固定范围 SQL 的执行失败。
- `failure_phase=BASE_RECORD_VALIDATION`、`P2_RECORD_VALIDATION`、`EXACT_MATCH_SCREEN`、`PRIVATE_PACKAGE_ASSEMBLY` 或 `PRIVATE_PACKAGE_WRITE`：数据库调用返回之后的本地核验/输出阶段。该字段不单独意味着语义隔离已通过。
- 未分类异常仍以 `SOURCE_CAPTURE_OR_RUNTIME_HOLD` 隐去正文，不能用临时 traceback 或打印 DSN 代替 SAFE 诊断。

首先在运行捕获器所用的**同一个** Python 环境做无网络驱动测试：

```bash
python3 - <<'PY'
import sys
print("PYTHON_EXECUTABLE =", sys.executable)
try:
    import psycopg
    from psycopg import pq
    print("PSYCOPG_IMPORT = PASS", psycopg.__version__)
    try:
        print("LIBPQ = PASS", pq.version())
    except Exception as exc:
        print("LIBPQ = HOLD", type(exc).__name__)
except Exception as exc:
    print("PSYCOPG_IMPORT = HOLD", type(exc).__name__)
PY
```

若缺驱动，先确认当前 `python3` 的 venv；仅在已授权私有 Python 环境安装 `psycopg[binary]`（psycopg3），不要改动数据库/角色/SQL/RLS 来绕过错误。若驱动通过，更新 Owner Mac 的公开捕获器到本 PR 最新版本（**备份已有脚本并对 GitHub 版本做字节比对**），用先前冻结的相同六个目录、Manifest、缺失的输出目录执行一次，回传新的 SAFE `reason_code` 与 `failure_phase`。若输出目录已有内容，不删除重试，先保全并核验。

任何这类定位都不改变 `P2_C=HOLD`、`P2_B_48_PROMPTS=NOT_GENERATED` 或 `train_admitted=0`。


## 2026-11-19 运行时故障根因：默认 tuple RLS 结果与 dict 校验器不兼容

Owner 已用 \`~/.local/share/storyforge/venvs/r60-owner/bin/python\` 确认 \`psycopg=3.3.9\`、\`LIBPQ=180006\`、\`DRIVER_CHECK_PASS\`。之后同一捕获器 \`--execute\` 仍返回：

\`\`\`text
status=P2_BASE336_SOURCE_EVIDENCE_HOLD
failure_phase=DB_SOURCE_FETCH
reason_code=SOURCE_CAPTURE_OR_RUNTIME_HOLD
database_accessed=null
private_file_created=false
\`\`\`

从公开源码定位到明确的**结构适配错误**：\`psycopg.connect(...).cursor()\` 的默认 \`fetchall()\` 返回 tuple 结果，而 \`r60_base336_p2_public_source_inventory_cpu.validate_rls_preflight()\` 要求每行 dict，调用 \`row.get("table_name")\`。该 mismatch 会触发 AttributeError，然后被捕获器的私有错误抑制层显示为泛化 HOLD。实际故障还可能包含别的问题，不能据此声称 SQL 已查询成功。

已修复 \`experiments/r58_quality/r60_base336_p2_source_evidence_capture_cpu.py\`：按游标 \`description\` 核验 \`table_name / rls_enabled / select_granted / policy_present\` 的返回列，严格将 tuple 转换为 dict，再调用**同一个** RLS 校验器；其他 SQL、角色名称、只读事务、RLS 策略、冻结故事范围和输出边界均不变。错误角色转 \`DB_ROLE_GUARD_HOLD\`，策略缺失转 \`DB_ROLE_RLS_POLICY_HOLD\`，结果列/形状不符转 \`DB_ROLE_RLS_RESULT_SHAPE_HOLD\`，不输出原始 DB 错误。新增三项不访问数据库的合成回归测试。

**下一动作**：复用 Owner Mac 已确认的 \`r60-owner\` Python venv，将捕获脚本与最新 GitHub 公开字节版本一致后，按上一个“Owner 已授权限定只读来源捕获”小节的相同 6 组冻结目录与 P2 Manifest 再执行一次 \`--execute\`。先检查原输出目录**不存在**；若已有目录或文件，不要删除或覆盖，改为保全现场并审查其来源，避免盲重试。此重试范围已经获得 Owner 只读访问授权，不需再次申请。

结果仍只回传 SAFE JSON；若再次 HOLD，按新 \`reason_code\` 和 \`failure_phase\` 定位，禁止打印 traceback / DSN / 私有字段，不削弱角色 / RLS / 版本约束。P2-C、P2-B、train_admitted 继续 HOLD / NOT_GENERATED / 0。


## 2026-11-19 R50 原始 50 条来源补集：已取得 Owner SAFE PASS

Owner 本轮返回 `R50_PROVENANCE_50_46_4_METADATA_PASS__P2_C_HOLD`，已保存 **原样 SAFE 回执**于 `docs/evidence/R60_P2_R50_50_46_4_PROVENANCE_COMPLEMENT_SAFE_20261119.json`。

此次 Owner 本地核验复用 `scripts/r60_r50_original50_complement_cpu.py` 内已有 provenance-only `jsonl/ids` 与 `r60_r50_exclusion_pair_cpu.py` 的 4 条排除集合函数，以及 `r60_r50_freeze_status_projection_cpu.py` 的受控 metadata reader；**没有调用会读取原始 R50 50 条密封题目正文的完整 complement audit**。检查对象与结论严格限定如下：

- 原始 R50 50 条 *provenance* 的固定大小及 SHA 通过，`original_50_provenance_verified=true`；不表示本轮读取/验过原始密封 50 条 case 的 bytes。
- 派生 46 条 *provenance* 对照原始 50 条的 `case_id`、原父行位置及 `source_story_id/source_session_id/cutoff_message_id/history_message_ids` 字段完整相符。
- Selection 4 条排除 ID 与 Admission 4 条排除 ID 集合一致，构成 `original50 - derived46 = excluded4`；`exact_50_46_4_metadata_complement=true`。
- P2 八条公开来源的 `story_id` 与原始 50 条 provenance `source_story_id` 集合的精确交集为 0；`p2_r50_exact_story_overlap=0`。
- `r50_sealed_content_opened=false`、`database_accessed=false`、`private_values_emitted=false`。
- `r50_complete_exclusion_verified=false`、`p2_c=HOLD`、`train_admitted=0` **不变**。

**阶段结论：R50 50/46/4 provenance metadata 补集已 PASS，不再重复原 46/46 预封存结构审计、4 条排除集合核验或 50/46/4 provenance 字段/行序检查。** 本结论没有正式验证原 50 条 case 的冻结字节、R50 Final Seal、R45 语义排除、隐藏 World 别名/同组件传播或 Protected/Reserved 完整 World roster 的覆盖；更不能将一次与 P2 的精确 Story ID 零交集外推为所有语义组件独立。

下一项只读最小动作：**复用** `~/.local/share/storyforge/r50/full-original-worlds/run.cGUPnjdx/R50_FULL_ORIGINAL_WORLD_INVENTORY_PRIVATE.json`（Owner 既有 inventory 记录：0600、10061 字节），审查其中是否存在可**权威绑定原 50 条 provenance 来源 Story/World**且可确认 Protected/Reserved 全范围的元数据 roster。没有明确 schema/来源版本/范围时，先做非正文、限定字段的结构检视，不猜字段路径、不打印 ID；若只能确认旧 `same_story_id_pair_count` 等聚合而无法证明完整 roster，单独维持 `R50_PROTECTED_RESERVED_FULL_METADATA_COVERAGE=HOLD`，不得再写“R50 50/46/4 未验证”。

其他独立主线门禁仍包括 Base336 172 Story 与 8 P2 全部 current+archived 世界/角色/开场语义来源审查（最近 `DB_BASE336_SOURCE_QUERY_HOLD`，暂停猜测性重试）、R47/R48/R55 完整历史曝光范围、actual-sent 版本、独立 Reviewer、Owner Freeze。未授权真实 48 prompt 或 GPU/HF 推理。
