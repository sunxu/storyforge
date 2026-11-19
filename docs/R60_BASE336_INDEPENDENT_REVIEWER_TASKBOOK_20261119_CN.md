# StoryForge R60 Base336 — 独立 Reviewer 正式任务书（v2）

日期：2026-11-19。适用范围：Base336 P2-C 八组成员级 Card/Opening 的跨 Train/Validation 关联候选。**本任务是语义组件证据审查，不是历史 actual-sent 还原，不是训练或模型评价，不得自动解锁 P2-C。**

## 一、责任分离

- **Owner/Coordinator**：保管八份 0600 原始文件、冻结 roster、V2 私有候选包；运行离线 `prepare`；按最小权限分发 10 对双侧证据及空白裁决表；检验 Reviewer 的真实身份/独立性、仲裁差异并冻结。Owner 不得代 Reviewer 编造 `independent_execution_attested=true`。
- **独立 Reviewer A**：未参与本轮候选边生成、先前 Codex 判定、此次 AI 分析的人或有可核验隔离记录的执行者；在不看既有建议和自动匹配层级的前提下独立审查。
- **Reviewer B（推荐）**：对相同 10 对重新独立审查；A、B 各自在隔离目录中保存结果，分别冻结后才能比较。如仅一位 Reviewer，则只能报告单人已审，不得声称双人一致。
- **Owner 仲裁**：对两位 Reviewer 的差异、证据不足、角色版本歧义作显式仲裁；任何未解决项继续 HOLD。当前工具**不自动提供**双 Reviewer 真实性或一致性证明。

## 二、输入、范围及版本约束

来源为 **8 份** `R60_BASE336_WORLD_GROUP_XX_CARD_OPENING_PRIVATE.json` 与已生成的 `R60_BASE336_COMPONENT_REVIEW_PACKET_PRIVATE_V2_20261119.json`。这批成员记录共 **59 条（38 current / 21 archived）**，覆盖 38 个唯一 Story / 82 个候选案例。离线工具只为 **10 对跨拆分不同 Story 候选**准备证据；它们在原始候选包中的编号为 `01、02、11、14、19、21、22、24、25、26`，不得当成连续 01–10。

此批审查不覆盖所有可能语义关联：未命中的近似改写、同名异源、同拆分的 16 对以及未上报的其他 Protected/Reserved 关系仍需另案核验。

**不要**提交私有文件到 GitHub，不要复制 R50 密封正文、提示/标准答案，也不要在公共日志输出原始 Story ID、角色名字、原文、修订 ID、SHA 或 Reviewer 私有身份。

## 三、机器可校验裁决格式

权威 JSON Schema：`R60_BASE336_INDEPENDENT_EDGE_REVIEW_SCHEMA.json`（Draft 2020-12），裁决 Schema 字符串为 `storyforge_r60_base336_independent_edge_review_private_v2`。

注意：早期 `r60_independent_reviewer_offline.py` 生成 **v1** 的自由文本 `source_evidence_ref_PRIVATE`，这不是本次正式格式；**必须使用随本任务书交付的 v2 脚本及新目录重新 `prepare`**。保留旧目录作历史证据，不删除、不覆盖，也不得直接修改旧 v1 文件伪装成 v2。重新 `prepare` 仅复用本地现有文件，**不访问数据库**。

空白表单（程序填充 `edge_ordinal` 与 SHA，Reviewer 不可修改）：

```json
{
  "schema": "storyforge_r60_base336_independent_edge_review_private_v2",
  "edge_ordinal": 1,
  "review_packet_sha256_PRIVATE": "<prepare 填入的 64 位小写 SHA256>",
  "decision": null,
  "reason_cn_PRIVATE": "",
  "source_evidence_refs_PRIVATE": [],
  "reviewer_key_PRIVATE": "",
  "independent_execution_attested": false,
  "source_version_reviewed": false,
  "historical_actual_sent_verified": false
}
```

填写时 `decision` 必须是以下三者之一：

- `SAME_SEMANTIC_COMPONENT`：两侧共享可识别的专属人物、人物身份/别名、独特组织/地点、关系链、事件或故事连续性。需说明共同事实及反例检验；这是**跨拆分组件冲突候选**，不是自动判训练已泄漏。
- `INDEPENDENT_TEMPLATE_ONLY`：有足够双侧上下文，明确相似性来自通用模板或常见题材而不是共享专属组件；列明比较了哪些独特实体和事件，不能仅凭“名字不同”“World 不同”或“找不到重复”判断独立。
- `INSUFFICIENT_EVIDENCE`：来源版本、人物背景、事件或其他关键证明不充分；不强迫得出 PASS。

`reason_cn_PRIVATE` 不少于 20 字，说明事实、区分点、局限性和证据逻辑。Reviewer 用实际审查身份填 `reviewer_key_PRIVATE`，并且**只有真实独立执行、实际审阅对应来源版本时**才能将 `independent_execution_attested`、`source_version_reviewed` 置 `true`。`historical_actual_sent_verified` **必须始终为 false**。

### 证据引用结构（必须同时有 A 和 B）

将 `source_evidence_refs_PRIVATE` 填为包含至少两项的数组，每项均必须精确对应 `EDGE_XX_EVIDENCE_PRIVATE.json` 中一侧的实际记录和非空字段，例如：

```json
"source_evidence_refs_PRIVATE": [
  {
    "side": "A",
    "source_record_index_PRIVATE": 46,
    "group_ordinal": 6,
    "source_kind": "current",
    "revision_id_PRIVATE": null,
    "field_path": "/character_PRIVATE/name"
  },
  {
    "side": "B",
    "source_record_index_PRIVATE": 43,
    "group_ordinal": 6,
    "source_kind": "current",
    "revision_id_PRIVATE": null,
    "field_path": "/opening_PRIVATE/0/content"
  }
]
```

**示例仅展示字段结构，不是已核对的有效路径或真实裁决；实际索引、修订号、路径必须从各自 Evidence 文件读取并确认。**

- `side`：仅 `A` 或 `B`；两侧都必须给出至少一个定位。一个有力结论可列多个事实来源。
- `source_record_index_PRIVATE`：Evidence 文件侧列表中的全局索引值，不是数组局部序号；必须与同一条记录的 `group_ordinal`、`source_kind`、`revision_id_PRIVATE` 相匹配。`current` 的修订号为 `null`；`version` 必须为正整数。
- `field_path`：从 `fields_PRIVATE` 起的 RFC 6901 JSON Pointer，如 `/character_PRIVATE/name`、`/characters_PRIVATE/0/upbringing`、`/opening_PRIVATE`。`~`、`/` 按 JSON Pointer 的 `~0`、`~1` 转义。路径要指向现存且非空的值；优先指向具有实质内容的末端字段，不要只引用空模板或根对象。
- 只引用实际对应的双侧记录；不允许借用其他 edge 的记录或编造不存在的历史版本。

**机器验收范围：**检查完整 Schema、候选包 SHA、八份来源字节 SHA 及证据页内容回放绑定、edge 编号、引用的 A/B 记录索引/版本/字段路径存在且非空、重复引用、理由长度以及声明格式。它**不能**证明引用文字支持 Reviewer 的真实结论，也不能独立证明身份、隔离或历史实际发送事实。

## 四、Owner 创建隔离审查材料

在 Owner Mac 内准备新版脚本、JSON Schema 与私有输入；权限控制及路径按实际本机环境设置：

```bash
set -euo pipefail
umask 077
BASE="$HOME/.local/share/storyforge/r60/private"
WORK="$HOME/workspace/storyforge-r60-p2-card-opening"
SCRIPT="$WORK/r60_independent_reviewer_offline.py"
SCHEMA="$WORK/R60_BASE336_INDEPENDENT_EDGE_REVIEW_SCHEMA.json"
INPUT="$BASE/r60-base336-group-cards-opening-20261115"
PACKET="$BASE/R60_BASE336_COMPONENT_REVIEW_PACKET_PRIVATE_V2_20261119.json"
REVIEW_A="$BASE/r60-base336-independent-review-20261119-v2-reviewer-a"
test -f "$SCRIPT" && test -f "$SCHEMA" && test -f "$PACKET"
test ! -e "$REVIEW_A" && test ! -L "$REVIEW_A"
python3 "$SCRIPT" prepare --inputs "$INPUT" --packet "$PACKET" --output-dir "$REVIEW_A"
```

预期 SAFE 状态：`REVIEWER_DOSSIERS_CREATED__DECISIONS_PENDING`，`review_edges=10`，`private_files_created=20`，`source_files_verified=8`。空白表单不可解释为已审。

**独立审查分发：**只交付 `EDGE_XX_EVIDENCE_PRIVATE.json` 和对应空白 v2 `EDGE_XX_DECISION_PRIVATE.json` 与本任务书；不要给候选包中自动 `evidence_tier`、旧 Codex 结论、此前 SAFE 风险等级或此对话的预判。Reviewer 在私有环境一条条独立完成并保存，不修改证据文件。

Reviewer B 使用自己的**独立新目录**和重新生成的空白表单，不与 A 共用可编辑裁决文件。若共享同一原始内容，只有真正隔离结果与审查过程才可称独立。

## 五、逐对审查步骤

对每条 `EDGE_XX_EVIDENCE_PRIVATE.json`：

1. 先记录各侧 current/archived 的版本与组别，识别同一 Story 的多组归属，避免重复计数。
2. 阅读 `character`、`characters`、`opening` 的**具体内容**，辨别相同人物、别名、关系、组织、地名、事件、剧情时间线及叙事起点。
3. 对比证据的时间上下文、编辑版本差异和矛盾之处；说明哪些事实属于常见模板、哪些具有独特辨识性。
4. 对应三态之一填写 JSON。填写 A/B 至少两条实际存在的字段路径，结合 `reason_cn_PRIVATE` 解释它们如何支持结论；只在真实满足时做独立性声明。
5. 对资料缺失、冲突证据、背景不明、历史 actual-sent 无法绑定的情形继续 HOLD 或仅给出“静态内容层”的有限判断，不延伸为训练泄漏结论。

## 六、Owner 验收及失败处理

```bash
python3 "$SCRIPT" verify \
  --packet "$PACKET" \
  --inputs "$INPUT" \
  --reviews-dir "$REVIEW_A" \
  --schema "$SCHEMA" \
  --safe-output "$BASE/R60_BASE336_REVIEWER_A_SAFE_V2_20261119.json"
```

`verify` 依赖 Python 包 `jsonschema`（Draft 2020-12）：缺失时在本地虚拟环境按受控依赖流程安装，而不是跳过 Schema 验证。由于 SAFE 输出为 create-only，**每个验收运行使用一个尚不存在的文件名**；若需要无文件检查，省略 `--safe-output`。不要删除已经生成的失败证据目录、篡改输入或继续尝试覆盖。

期望状态：

- `REVIEW_INCOMPLETE_HOLD`：存在未填或未真实确认独立/版本审查的记录。只允许归档为部分进度。
- `HOLD` + 固定 `reason_code`：Schema 错误、引用到错误 Side/record/version、JSON Pointer 不存在等硬错误；返回 Reviewer 修正，不得跳过。
- `REVIEW_FORMS_COMPLETE__OWNER_INDEPENDENCE_CHECK_PENDING`：十份表单格式、A/B 引用存在与绑定、两项自述声明都齐备。**不等于语义审查正确或真正 Reviewer 独立，更不意味着 P2-C PASS**。

Owner 另行核实 Reviewer 身份、执行环境、先前参与经历、结果冻结、A/B 分歧和冲突边处理。已确认的语义组件标签保留在 Owner 私有环境，复用仓库 `src/storyforge_dataset/world_isolation.py` 的 `validate_component_review_assignments` 和 `component_split_conflicts`，不创建另一套世界隔离算法。

## 七、总体门禁及禁止动作

本审查完成只解决这 10 对候选边的成员内容语义裁决。全量 Base336 组件隔离、实际历史发送版本、R50 全量 Protected/Reserved metadata-only 覆盖、旧已暴露集合闭合、其他独立评测集、Reviewer 真独立性、Owner 冻结仍须分别核实。

始终保持 `P2_C=HOLD`、`P2_B_48_PROMPTS=NOT_GENERATED`、`train_admitted=0`、`quality_v1_admitted=0`、`gpu_started=false`、`hf_jobs_submitted=0`、`model_requests=0`。不得自动删除、重分配或重新训练任何冻结案例；不得上传原始内容、私有裁决或源哈希到公共仓库。