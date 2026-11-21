# Base336 独立 Reviewer v2 JSON Schema 与执行合同

日期：2026-11-19。完整交付文件已在 Owner 工作目录中下发：`R60_BASE336_INDEPENDENT_EDGE_REVIEW_SCHEMA.json`（Draft 2020-12）、`R60_BASE336_INDEPENDENT_REVIEWER_TASKBOOK_20261119_CN.md` 和 `r60_independent_reviewer_offline.py`（v2）。

## 与原 v1 的差异

- 原 v1 裁决字段 `source_evidence_ref_PRIVATE` 是自由字符串，不能机器校验 A/B 两侧真实字段。
- v2 裁决 schema 为 `storyforge_r60_base336_independent_edge_review_private_v2`，取代自由文本字段的 `source_evidence_refs_PRIVATE` 是结构化数组。每条引用包括 `side`（A/B）、`source_record_index_PRIVATE`、`group_ordinal`、`source_kind`（current/version）、`revision_id_PRIVATE`、`field_path`（RFC6901 JSON Pointer）。
- `verify` 校验完整 Draft 2020-12 Schema、A/B 至少各一个定位、实际记录 / 版本 / group / 非空字段路径、证据页与源文件重建的内容一致性、原始八组字节 SHA pin、packet SHA pin、edge 编号、理由及声明。不满足时返回固定 `HOLD` 代码且不泄露私有内容。
- `verify` **新增必填** `--inputs` 以核验原始八组数据的完整性；须提供 `--schema` 文件路径（默认脚本同目录）；需要 Python `jsonschema` 包。原 v1 裁决文件不自动升格；在新的私有目录重新 `prepare` v2 空白表单，旧文件一律保留、不得覆盖。
- 审查候选的原始边序号为 `01,02,11,14,19,21,22,24,25,26`，不应编号 01–10。

## 验证与独立性边界

Owner 用当前 8 份源文件及原有 V2 候选包对改进工具做离线测试：
1. `prepare` 输出十对证据页及十张空白 v2 表单，输出 `REVIEWER_DOSSIERS_CREATED__DECISIONS_PENDING`；
2. 对未填表单运行 `verify` 正确返回 `REVIEW_INCOMPLETE_HOLD`；
3. 用显式标记为 synthetic 的单份填写表检查 A/B 合法引用绑定，返回 1 条已填、9 条待填且总体仍 HOLD；
4. 修改索引得到 `EVIDENCE_RECORD_BINDING_HOLD`；修改证据页正文得到 `EVIDENCE_SOURCE_CONTENT_BINDING_HOLD`。**以上仅为合成测试，不是独立 Reviewer 的真实决定**。

独立 Reviewer 应独自阅读两侧 Card/Opening（含 current/archived），三态决定 `SAME_SEMANTIC_COMPONENT` / `INDEPENDENT_TEMPLATE_ONLY` / `INSUFFICIENT_EVIDENCE`，理由需说明具体角色、关系、组织、事件、版本依据和不确定性。Owner 单独核验身份、隔离、盲审和争议仲裁；表单自述不能独立证明独立性。第二 Reviewer 推荐另目录独立执行，不得预看第一位结论。

## 不变门禁

十对候选完成仍不能证明全量 Base336 组件隔离，也不证明历史 actual-sent 版本、R50 完整 Protected/Reserved metadata-only 排除、旧曝光集合闭合和 Owner 冻结。维持：
```text
INDEPENDENT_REVIEW = NOT_EXECUTED
ACTUAL_SENT = NOT_VERIFIED
P2_C = HOLD
P2_B_48_PROMPTS = NOT_GENERATED
TRAIN_ADMITTED = 0
QUALITY_V1_ADMITTED = 0
GPU_STARTED = false
HF_JOBS_SUBMITTED = 0
```
