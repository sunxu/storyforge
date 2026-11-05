# R58 Priority3 — 条件性 11 条历史窗口预检回执（SAFE）

日期：2026-10-30。证据等级：**Owner 提供终端 JSON 回执，非独立直接读取私有来源包**。本报告不存储任何私有 ID、消息、故事卡、指纹或完整原始 manifest。

## Owner 已报告的结果

- `R58_CONDITIONAL_HISTORY_WINDOW_STRUCTURE_PASS__RUNTIME_REPLAY_HOLD`。
- 三条来源路径 `AUTHOR`、`CURRENT_PUBLIC`、`OLD_PUBLIC` 的条件性历史窗口均为 **11 条（3/3 PASS）**；附近延迟指标 `historyMsgCount == 11` 为 **3/3**，但指标使用同 session、时间邻近关联，**不是精确 request_id JOIN**。
- Event runtime：`CURRENT_PUBLIC` 与 `OLD_PUBLIC` 的前一 Assistant `v2EventRuntimeAfter` 与目标 `v2EventRuntimeBefore` 达到 JSONB 结构相等 **2/2**；`AUTHOR` 未记录对应字段（`NOT_PRESENT`，不等同验证成功）。
- 三条路径均出现 **5** 条 `mutation_revision > 0` 的条件窗口消息；未发现 `continue` 消息或 Assistant 原文包含 `<` 的结构化清理候选（这并不排除其他策略清理）。
- `actual_runtime_history_bytes_verified=false`，`actual_runtime_prompt_bytes_verified=false`，`training_admission=HOLD`。

## 修订行数的含义：不要错判为五次正文编辑

2026-10-30 对 Supabase **仅查询数据库元数据和触发器函数定义**（无故事文本或真实用户数据）：

`public.maintain_v2_message_mutation_revision()` 在 INSERT 置 revision=0；UPDATE 比较 `role/content/status/metadata/partial_content`，任一变化即 `OLD.mutation_revision + 1`，其他 UPDATE 保持不变。因此 **revision>0 既可能是流式回复完成时 status/partial_content 更新，也可能是正文或元数据变更；光凭该数字无法区分**。

`public.capture_v2_chat_message_ledger()` 对 INSERT 与业务列 UPDATE/DELETE 记录 Ledger；UPDATE 的业务列包括 `role/content/metadata`，但 **status/partial_content-only UPDATE 不会记录为业务变更**。先前捕获的 `post_target_ledger_events=0` 可作为 Ledger 覆盖的业务变更证据，但不是所有字段/所有路径的字节级无变更证明。

**5 条 revision-positive 恰好与一个 11 条 User/Assistant 交替窗口中的 5 条 Assistant 数量相同；这是待查假设，不是已验证相等。** 离线工具 `audit_priority3_mutation_revisions.py` 将在 Owner 私有来源包上按角色核查统计，不会泄露 ID、正文或 hash。即使发现 5/5 Assistant 正好有正 revision，也不能据此宣称历史正文没有被编辑。

## 历史摘要游标与执行代码差别

固定源码 `sunxu/RolePlay@e9fe29c42434caeb0bac5acc91845ab4741ecb2b` 中，`pruneHistoryBySummary()` 输入 `v2Session.last_summary_turn`（在线 `story_v2_sessions` 字段）。当前离线预检从 **prior checkpoint snapshot** 读取 `last_summary_turn`，尚未证明请求当时它与 session 实际字段一致。固定 Git commit 也不等于已确认线上历史部署 SHA。

因此 `11/11` 是 **条件结构符合**，不是 `history bytes exact`，更不是 `provider prompt bytes exact`。

## 下一步（离线私有，不改冻结物料）

新增 `experiments/r58_roleplay_replay/audit_priority3_mutation_revisions.py` 和 8 条纯合成测试 `test_audit_priority3_mutation_revisions.py`，执行方式：

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
python3 -m unittest discover \
  -s experiments/r58_roleplay_replay \
  -p 'test_audit_priority3_mutation_revisions.py' -v

# 仅当新增合成测试通过，再执行已固定的本地来源包：
python3 experiments/r58_roleplay_replay/audit_priority3_mutation_revisions.py \
  --private-dir "$HOME/.storyforge-r58-private/priority3_source_20261030_first_capture"
```

新工具只输出安全角色计数与 HOLD，不访问生产 DB、不修改本机来源包。**新 8 条测试和真实离线分类尚待 Owner 执行。**

后续若需要 `as-of` 真正原文证明，必须设计以冻结案例 ID 为键、只读且保密的 Ledger/请求日志回放核验，不得重新选择/覆盖三条故事来源，也不能假定不存在历史部署/请求参数差异。Train/Val/Teacher 准入仍为零；PR #7 Draft、Skill v0.1 不变。
