# Base336 P2-C：独立 Reviewer 可执行流程（SAFE）

日期：2026-11-19；状态：**准备工具已验证，独立 Reviewer 尚未执行，全部门禁 HOLD**。

## 来源与范围

Owner 提供 8 组私有 Card/Opening、冻结 roster、代表 World、Codex HOLD 及可复现的 V2 候选包。当前跨 Train/Validation 候选为 10 条不同 Story 边（强证据层 7、扩展候选 3），总 16 Story / 35 候选案例。不得将这些机械候选自动判为语义泄漏或独立 Reviewer 结论。

已有 `r60_base336_component_review_packet.py` 只构造候选包，不包含 Reviewer 决策执行器。因此本轮提供离线工具 `r60_independent_reviewer_offline.py`（Owner 获取并运行，**不把私有输入传到 GitHub**），提供 `prepare` 与 `verify` 两个命令：

1. **prepare**：校验原有 V2 private packet 与 8 份源文件 SHA、roster 绑定、59 个 record locator；仅在 Owner 私有 `0700` 新目录中以 `0600` create-only 生成 10 份双侧证据页、10 份空白 Reviewer 裁决表。证据页不包含自动建议的 HIGH/CANDIDATE 结论；不访问数据库，不读取 R50，也不运行任何模型。
2. **independent review**：由未参与候选筛选、未参与旧 Codex 结论的人或隔离执行者阅读 A/B 完整 current/archived Card/Opening；每对在 `SAME_SEMANTIC_COMPONENT`、`INDEPENDENT_TEMPLATE_ONLY`、`INSUFFICIENT_EVIDENCE` 三种结果中择一，填写具体依据、私有来源定位及 Reviewer 标识。只有本人真实确认时才声明独立执行、来源版本已审。**另开聊天不自动等于独立审查**。
3. **verify**：校验 10 份独立 Review 表的 packet SHA、edge 次序、非空理由与证据引用、声明值；stdout 仅 SAFE 聚合（决定数、未完成数、自述独立数、版本已审数），不得输出故事正文、ID、版本、映射或私有 SHA。此工具不能替 Owner 证明独立性。
4. **Owner**：核实执行者真实独立性、证据可靠性与裁决范围；在私有环境对经裁决的全部相关 Story 赋组件 ID，并复用 `src/storyforge_dataset/world_isolation.py` 的 `validate_component_review_assignments` / `component_split_conflicts` 检查拆分冲突。缺失、未完成及未知继续 HOLD，不自动修改冻结数据。

离线工具已以当前 8 份私有组文件 + V2 私有候选包作仅本地运行验证：`prepare` 成功生成 20 个文件，空白表单的 `verify` 正确返回 `REVIEW_INCOMPLETE_HOLD`、`PENDING=10`。**尚未取得任何真实 Reviewer 裁决**。

Owner 私有执行手册名称：`R60_Base336_Independent_Reviewer_Execution_Guide_CN.md`；本机 Python 工具：`r60_independent_reviewer_offline.py`。文件由当前对话交付，不将私有候选包或原始 Card/Opening 写入本仓库。

## 固定门禁

```text
INDEPENDENT_REVIEW = NOT_EXECUTED
REVIEWER_DOSSIERS = PREPARE_TEST_PASSED_ONLY
OWNER_FREEZE = NOT_PERFORMED
HISTORICAL_ACTUAL_SENT = NOT_VERIFIED
R50_COMPLETE_EXCLUSION = HOLD
P2_C = HOLD
P2_B_48_PROMPTS = NOT_GENERATED
TRAIN_ADMITTED = 0
GPU_STARTED_THIS_REVIEW = false
HF_JOBS_SUBMITTED_THIS_REVIEW = 0
```
