# R60 Base336 P2 Protected Crosswalk：下一 Agent 接手提示词（2026-11-18）

> **任务类型：Owner-local 私有证据核验与交叉隔离审查。不是训练、推理、Supabase 重抽取或提示包生成任务。**
>
> 仓库：`sunxu/storyforge`；分支：`r60/common2-cpu2-owner`。交接时必须重新核验远端 HEAD、Actions 和工作区。

## 唯一首要目标

完成 R60 Base336 P2 保护集交叉核验的证据准备与实现，但**第一步只能做 Owner Mac 私有文件元数据盘点**。当前尚未收到盘点输出，不能假设私有文件存在、完整或 Schema 与历史预期一致。

| 子项 | 状态 | 已知事实 |
|---|---|---|
| P2-A Supabase 公开来源 Inventory | READY | 8 条来源、5 位作者、8 个不同 World JSON；revision / snapshot / permission 绑定通过；指定范围精确 World overlap=0 |
| P2-C Base336 保护集语义隔离 | HOLD | 历史 8 组 roster/evidence 尚未完成语义裁决；成员级证据完整性待核验 |
| P2-C R50 Protected/Reserved 排除 | UNKNOWN / HOLD | 只允许完整 metadata-only 清单，不允许读取 R50 正文 |
| P2-C R47/R48/R55 暴露排除 | PARTIAL METADATA / UNKNOWN / HOLD | R47/R48 20-case 结构已核验但无 Story ID 映射；R55 私有 Index 文件存在，内容 / Schema / 覆盖未核验 |
| P2-C actual-sent 版本绑定 | UNKNOWN / HOLD | 代表性 World evidence 未证明实际发送版本 |
| P2-C Reviewer 独立性与 Owner 冻结 | HOLD | 尚无完整可复核结论 |
| P2-B 真实 48 条提示包 | NOT_GENERATED | 没有真实 JSONL / Manifest / SHA256；9/9 是合成校验器测试 |
| P3 Base/Adapter 评估适配器 | WAIT | P2-C 通过前不实现正式 Pairer/Profile/Backend |
| P4 GPU 推理 | NOT_AUTHORIZED | 必须另行取得具体输入、模型、Flavor、时长、Token 上限、输出前缀和预算授权 |

## 第 0 阶段：先核验仓库与权威材料

先读取 `AGENTS.md`、本文件，以及：

1. `docs/R60_BASE336_POST_TRAIN_NEXT_AGENT_HANDOFF_20261117_CN.md`
2. `docs/plans/R60_BASE336_POST_TRAIN_QUALITY_EVALUATION_20261117_CN.md`
3. `docs/plans/R60_BASE336_SUPABASE_PUBLIC_STORY_P2_ADDENDUM_20261117_CN.md`
4. `docs/plans/R60_BASE336_P2_PROTECTED_CROSSWALK_EVIDENCE_INDEX_20261118_CN.md`
5. `docs/R60_BASE336_NEXT_AGENT_START_PROMPT_20261117_CN.md`
6. `skills/storyforge-roleplay-sft/SKILL.md` 与 `MANIFEST_SAFE.json`
7. `docs/standards/GOLD_QUALITY_PIPELINE_CN.md`
8. `src/storyforge_dataset/world_isolation.py` 与 `tests/test_world_isolation.py`

只读查询当前分支 HEAD、工作流、PR 和相关 Actions。区分文档提交、合成 CI、真实数据库访问和 HF Job；不得把历史 CI PASS 当作当前 HEAD 的验证。

## 第 1 阶段：Owner Mac 私有文件 metadata inventory（唯一允许的第一项本地动作）

先向 Owner 取得本轮 inventory 输出。若尚未执行，提供以下命令让 Owner 在 Mac 执行。它只列出匹配文件的**文件名、字节数、权限、修改时间**，不打开文件内容。

```bash
python3 - <<'PY'
from pathlib import Path
from datetime import datetime, timezone
import stat

h = Path.home()
roots = {
    "P2_SOURCE": h / ".local/share/storyforge/r60/private/r60-p2-public-source-inventory-20261118",
    "BASE336_WORLD": h / ".local/share/storyforge/r60/private/r60-base336-world-cross-review-20261115",
    "R50_DERIVED": h / ".local/share/storyforge/r50/run.dWgMu5/private/derived",
    "R50_PRIVATE": h / ".local/share/storyforge/r50/run.dWgMu5/private",
    "R50_FULL_METADATA": h / ".local/share/storyforge/r50/full-original-worlds/run.cGUPnjdx",
    "R50_R45_GATE": h / ".local/share/storyforge/r50/r45-full-source-gate",
    "R47_EXPOSURE": h / ".local/share/storyforge/r47/r47-20261014T091647Z-637890/coordinator",
    "R48_EXPOSURE": h / ".local/share/storyforge/r48",
    "R55_EXPOSURE": h / ".local/share/storyforge/r55",
}
terms = (
    "MANIFEST", "SAFE", "EXPOSURE", "CROSSWALK", "INVENTORY",
    "RECEIPT", "DECISION", "PROVENANCE", "ADMISSION", "LEDGER",
    "ROSTER", "PROTECTED", "RESERVED", "SOURCE", "AUDIT",
    "REVIEW", "EVIDENCE", "CARD", "OPENING",
)
for label, root in roots.items():
    print(f"\\n=== {label} ===")
    if not root.is_dir():
        print("DIRECTORY_MISSING")
        continue
    files = sorted(p for p in root.rglob("*")
        if p.is_file() and any(t in p.name.upper() for t in terms)
        and p.name != ".DS_Store")
    print(f"matching_files={len(files)}")
    for p in files[:100]:
        s = p.stat()
        mtime = datetime.fromtimestamp(s.st_mtime, timezone.utc).isoformat()
        print(f"{p.name} | {s.st_size} bytes | {stat.filemode(s.st_mode)} | {mtime}")
    if len(files) > 100:
        print("TRUNCATED_TO_100")
PY
```

若文件名含敏感标识，Owner 应先脱敏再回传。不要输出 Story ID、作者映射、正文、SHA256 或本机绝对路径；不要上传私有文件。文件名和时间不能证明 Schema 正确或保护集覆盖完整。

### 1.1 Inventory 后的诊断规则

- 将文件分为 P2 Source Manifest、Base336 roster / decision template / representative World evidence / Codex review / card-opening evidence、R50 metadata-only roster / SAFE、R47/R48/R55 source/exposure Manifest / SAFE。
- 每项标记 PRESENT、MISSING、DUPLICATE/AMBIGUOUS、PERMISSION_HOLD、STALE_OR_UNBOUND 或 UNKNOWN。
- 此前 `r60_base336_group_cards_opening_cpu.py --execute` 返回泛化 `BASE336_CARD_OPENING_EVIDENCE_HOLD`，没有 failure phase / reason。先只读核对既有 SAFE 聚合字段和输出文件元数据。
- **禁止再次运行全量 `--execute`**；禁止重跑 DB 查询、重建 roster/template/evidence、删除或覆盖任何既有输出。只有确认失败阶段、Schema、输出状态并取得 Owner 对具体最小修复动作的重新确认后，才可提出修复。
- 不读取 R50 正文、答案、提示或密封内容；R50 仅允许 Owner 明确授权的完整 metadata-only 清单。
- 缺少完整保护集输入时，逐项 HOLD；不得用新 Supabase 查询替代历史保护集证据。

## 第 2 阶段：复用 Base336 既有 World 证据

先阅读源码与测试，不凭文件名推断功能：

- `experiments/r58_quality/r60_base336_world_cross_split_private_roster_cpu.py`：冻结 336 cases / 172 stories 的 8 组精确 current/archived World JSON 关联 roster；不是语义裁决。
- `experiments/r58_quality/r60_base336_world_review_decisions_template_cpu.py`：8 组决策模板，初始全部 HOLD。
- `experiments/r58_quality/r60_base336_world_group_source_evidence_cpu.py`：每组一个代表性 World source evidence；不是 38 个成员的完整角色卡/Opening 证据。
- `experiments/r58_quality/r60_base336_group_cards_opening_cpu.py`：设计上覆盖 8 组 / 38 个故事的 current / archived `character`、`characters`、`opening`；此前全量执行泛化 HOLD，不可盲目重跑。
- `experiments/r58_quality/r60_base336_world_linkage_screen_cpu.py`：精确结构关联屏查，不证明语义别名完整。
- `experiments/r58_quality/r60_base336_world_metadata_coverage_cpu.py`：冻结来源结构化元数据覆盖，不证明角色卡认证或语义隔离。
- `src/storyforge_dataset/world_isolation.py`：唯一共享组件冲突检查；复用 `validate_component_review_assignments()` 与 `component_split_conflicts()`，不得复制第二套算法。

**必须区分两组 8：**
- P2 新公开来源：8 条 Supabase 故事、5 位作者、8 个不同 World JSON。
- Base336 历史审查：8 组精确 World 值关联，影响 38 个故事、82 个 case；7/8 当前 World 值跨 Train/Validation，8/8 语义裁决仍 HOLD。

每个 semantic component assignment 必须有可追溯的成员级 current/archived source evidence。不能仅凭 Story ID、JSON/hash 不同、GPU Run 后创建、generic template 标签或 AI 总结判定语义独立。共享 helper 只验证结构和已声明冲突，不替代语义判断。

## 第 3 阶段：完整保护集 crosswalk

对 P2 的 8 条新来源做精确身份、版本、语义组件和暴露历史交叉核验，至少覆盖：

1. Base336 冻结 Train/Validation 私有来源 roster，以及相关 current/archived World 与角色卡 / Opening 证据。
2. R50 完整 Protected/Reserved World **metadata-only** roster；必须证明清单完整，禁止访问密封正文、提示、答案。
3. R47/R48/R55 已暴露开发题、来源及语义变体的完整 exposure/source Manifest；历史脚本、局部 SAFE 或单一哈希不等于完整覆盖。
4. 其他已冻结独立评测集和未解决保护集合。
5. 历史 actual-sent / delivered prompt 版本、来源 revision 和上下文时间；缺少真实发送记录时保持 UNKNOWN/HOLD。

每类保护集独立输出覆盖范围、输入版本绑定、匹配方法、未覆盖项和 SAFE。精确相等、语义关联、时间边界、实际发送版本、权利范围和 Reviewer 独立性是不同门禁，不得合并成模糊 PASS。

## 第 4 阶段：适配器开发门槛

只有在 Owner-local inventory 确认真实文件存在、Schema 可读、版本一致、保护集范围完整后，才允许设计版本化 Owner-local 薄适配器：

- create-only，禁止覆盖已有输出。
- 私有输入和逐案输出只留在 Owner Mac；GitHub / CI / 聊天只接收不含私有值的 SAFE 聚合。
- 复用 `world_isolation.py`，不复制组件冲突算法。
- Base336、R50、R47/R48/R55、其他保护集、actual-sent、Reviewer independence 分开记录；任一覆盖不完整则总状态 HOLD。
- 先做 synthetic-only 测试，覆盖 PASS/HOLD/REJECT、缺失、重复、版本漂移、覆盖缺口、跨 split、权限隐私、create-only 和 SAFE 无私有值。
- 不猜 Schema、不编造输入字段、不设置默认 PASS。

## 第 5 阶段：P2-B / P3 / P4 顺序

- P2-C 全部保护集交叉核验、独立 Reviewer 复核和 Owner 冻结完成前，真实 48 条提示 JSONL / Manifest **保持 NOT_GENERATED**。
- P2-C PASS 后才按 Owner 当前授权构造内部评估提示；逐条检查来源忠实性、原文长段复用、未来信息泄漏、隐藏指令混入及合成 NPC 标记，并由 Owner 冻结真实 prompt SHA256。
- P2-B 完成不自动授权模型推理。
- P3 只在 P2 完成后设计 Base/Adapter 薄适配器；复用 `generation_eval.worker`、HF Runtime、GenerationBackend 和 Quality-v1 六维规则。
- P4 GPU 推理必须另行明确授权，包含输入、模型 Revision、Flavor、时长、样本数、Token 上限、Bucket 前缀和预算。

## 交付物

**Owner Mac 私有：** metadata inventory、输入证据版本/覆盖清单、逐案精确/语义 crosswalk、来源引文、Reviewer 决策、私有 SHA Manifest、SAFE 汇总、Owner 冻结回执。

**GitHub 可公开：** Schema 确认后才提交的版本化适配器和 synthetic-only 测试、技术规范、任务书、交接提示词、无私有数据的证据索引、CI 结果和 commit SHA。

不得提交私有 Source Manifest、Story ID、作者映射、正文、逐案证据、私有 SHA 或本机绝对路径。

## 永久安全边界

```text
database_modified = false
gpu_started = false
hf_jobs_submitted = 0
model_requests = 0
train_admitted = 0
quality_v1_admitted = 0
model_promoted = false
protected_crosswalk_verified = false  # 直到完整 P2-C 证据和 Owner 冻结通过
```

不重跑 Supabase 来源查询；不访问 R50 正文；不修改 293/43、checkpoint、训练产物或 Gold Manifest；不做 GPU/HF 推理或训练；不扩大 Owner 已确认的内部评估提示构造权利范围。

## Agent 首次回复格式

先报告：当前 GitHub HEAD / Actions；权威材料阅读确认；Owner-local metadata inventory 是否收到；逐类文件 PRESENT/MISSING/AMBIGUOUS/HOLD；下一项最小无副作用动作。

本次已收到 R47/R48/R55 的部分 metadata / shape inventory，不要重复盘点这些已确认文件；下一步进入其私有 Index 的结构 / 覆盖 SAFE 检查。对 Base336、R50 或其他尚未提供 inventory 的保护集，仍只做文件元数据确认；缺失时保持对应 HOLD。任何情况下不得猜测 Schema 或执行数据库提取。


## 2026-11-18 Owner R47 / R48 / R55 metadata 审计增量

Owner 已返回 metadata / shape-only inventory。详细结果见：
docs/evidence/R60_P2_R47_R48_R55_SOURCE_SHAPE_AUDIT_20261118_CN.md。

- R47 Manifest 有 20 个 Sample 条目，字段为 sample_id、prompt_sha256、source_line；compiled Test 有 20 条 id/messages/metadata；prompts 有 20 条 messages。现有证据链没有证明逐案 Story ID 映射。
- R48 是同一批已暴露的 R47 20 个 Prompt，四臂共 80 条回复；不增加独立案例，也没有补出缺失的 Story ID crosswalk。
- R55 私有 Coordinator Index 和 SAFE 文件仅通过文件系统元数据确认存在；内容、实际 Schema、receipt / version 绑定和覆盖范围均未验证。
- 因此 P2 × R47/R48/R55 精确 Story ID crosswalk 仍为 UNKNOWN / HOLD；语义暴露排除仍为 HOLD。不得根据 JSONL 行序、source_line、通用 id、哈希或文件名推断身份。
- 下一步：Owner-local 对 R55 私有 Index 做 Schema / 数量 / 覆盖 SAFE 检查，并寻找权威 Sample → Story ID 来源绑定。不访问 DB / R50 正文，不启动 GPU / HF，不发起模型请求，不生成提示包。


## 2026-11-18 补充：R47/R48/R55 Sample → Story ID 代码链已定位

不要再将任务描述为“仓库没有 Sample → Story ID 映射路径”。代码复核已找到以下绑定链：

- R47：Manifest \`sample_id / prompt_sha256 / source_line\` → canonical Test 对应行（完整 role/content prefix 与 prompt hash 一致）→ 该行 \`metadata.story_id\`。依据：\`scripts/prepare_blind_eval.py\`、\`scripts/audit_v01_integrity.py\`、\`scripts/v02_r48_four_arm_build.py\`。
- R48：固定相同 canonical Test SHA 和同一 20-case prompts，不增加独立案例；继承 R47 的 Story ID 映射。
- R55：第一层 Index 的 \`source_sample_id_private\` 回连 R47 Sample；第二层的 \`original_candidate_token_private\` 回连第一层；第三层的 \`original_second_candidate_token_private\` / \`original_first_candidate_token_private\` 回连第二层 / 第一层。

**当前仍 UNKNOWN / HOLD 的原因是实际 Owner-local 文件值和 SAFE receipt 尚未核验，不是代码路径不存在。**

### 下一项执行

1. 对 R47 Manifest、prompts、canonical compiled Test、R48 Source Audit、P2 private source Manifest 做 Owner-local SAFE：检查 Test SHA、20/20 prompt prefix / hash / source_line、20/20 metadata.story_id，再输出 P2 × R47/R48 exact overlap count。
2. 对 R55 三个私有 Index 做 schema / record count / token link / first-layer 20-case coverage / receipt SHA binding SAFE。
3. 审查 \`preflight-package/scripts/r55_dev_source_preflight.py\`、对应测试及 \`exposed20/sources/R55_OLD_R47_SOURCE_PREFLIGHT_SAFE.json\`，确认它是否将 R55 原始 20-case 与 R47 Manifest 绑定。
4. 用第一层 \`source_sample_id_private\` 经 R47 crosswalk 得到 Story ID，与 P2 Manifest 的 8 个 Story ID 做精确比较。只输出计数与布尔值，不输出 ID、作者映射、正文或 SHA。
5. 任何输入缺失、receipt 不匹配、覆盖不完整或 token 链断裂均保持 HOLD；即使 exact overlap=0，也不代表语义隔离 PASS。

不要上传 R55 私有 Index / Key / Reviewer 文件，不读取 R50 正文，不访问数据库，不运行 GPU/HF / 模型请求，不生成正式 48 条提示包。


## 2026-11-18 R55 三层索引 SAFE 已通过：后续不要重跑

Owner 本机实际输出 `R55_THREE_INDEX_LINK_AND_RECEIPT_PASS__P2_C_HOLD`：三个 Index 的 Schema、Prep Index SHA、token 唯一性通过；76/68/46 records；第一层对冻结 R47 Manifest 20/20 source samples 覆盖，extra/missing 皆 0，20 个 case indices 合法；第二层 68/68 链接及第三层双回链均通过。该有限证据可以直接复用。

**新的下一步**：只读检验 canonical compiled Test 的固定 SHA、R47 20 个 prompt prefix / SHA / source_line / Sample ID 公式、`metadata.story_id` 完整性、R48 Source Audit 的 canonical Test SHA 与 prompt / manifest SHA 绑定，并比较 P2 8 个 Story ID 与历史 20 个 Story ID 的精确交集。仅输出 SAFE 数字 / 布尔值。不要再运行 R55 三层 index link 检查，勿因本轮 PASS 宣布 P2-C 通过。
