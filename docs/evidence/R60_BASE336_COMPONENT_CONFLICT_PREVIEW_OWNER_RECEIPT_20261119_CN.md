# R60 Base336 — Owner Mac 组件候选冲突预览 SAFE 回执登记（2026-11-19）

## 来源与验收

Owner 在本轮对话提交了由其 Mac 运行 `r60_base336_component_conflict_preview_cpu.py` 后产生的 SAFE JSON。所提交的字段与仓库既有 `docs/evidence/R60_BASE336_COMPONENT_CONFLICT_PREVIEW_SAFE_20261119.json` 内容一致；因此不再创建第二份相同统计文件，不覆盖已封存的私有产物。这里是**用户提交的运行回执核对**，不是本助手远程读取 Owner Mac 或复跑其私有证据所得结论。

- `status=BASE336_COMPONENT_CONFLICT_PREVIEW_READY__P2_C_HOLD`
- `candidate_cross_split_edges=10`；`candidate_cross_split_components=6`
- `component_story_sizes=[2,2,2,2,3,5]`
- `candidate_affected_stories=16`；`candidate_affected_cases=35`
- `all_38_stories_semantic_isolation_verified=false`
- `semantic_component_identity_owner_certified=false`
- `reviewer_b_independence_verified=false`
- `reviewer_b_aggregate_checked=false`（没有附传可选 B SAFE 回执；不等于 B 的先前 SAFE 校验失败）
- `reviewer_edge_level_binding_verified_here=false`（工具使用十条候选边的保守假设，而不是逐条回放 B 的私有裁决）
- `historical_actual_sent_verified=false`；`r50_complete_exclusion_verified=false`
- `p2_c=HOLD`、`p2_b_48_prompts=NOT_GENERATED`、`train_admitted=0`
- `database_accessed=false`、`gpu_started=false`、`hf_jobs_submitted=0`、`private_values_emitted=false`

## 使用边界

1. Owner 私有目录中的 6 个候选组件→16 Story→35 案例对应表，只作**临时隔离观察清单**。未证明已经将这些案例从训练、校验、评分或生成入口实际排除。
2. 本轮工具只对 10 条跨拆分候选边采用同组件假设，不会自动合并其他 16 条同拆分候选，也不穷尽其余 22 个 Story 的共享世界问题。
3. 不能把组件连通性/结构冲突的 SAFE PASS 当作正式语义独立性通过、Reviewer B 资格通过、actual-sent 版本通过或 R50 全量排除通过。
4. 如要确认应用层隔离，需另建**只读**针对消费入口的效果核验：明确输入冻结 roster、准备使用的候选集合以及未误入的 35 案例；默认失败关闭、不修改冻结 split。没有这项证据，不更新 `train_admitted` 或 `P2_C`。
5. 接下来可**并行**推进原历史 actual-sent 来源版本绑定、R50 完整 protected/reserved metadata-only 排除、R47/R48/R55 旧暴露集合闭合；B 资格 HOLD 不阻塞这些独立的只读证据核验。

本文件不含私有 Story ID、候选位置映射、原始角色卡、版本号、原文或 SHA；既有 SAFE JSON 和 Owner 私有快照分别保持不变。
