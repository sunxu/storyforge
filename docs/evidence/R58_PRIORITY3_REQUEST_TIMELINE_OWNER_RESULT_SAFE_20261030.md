# R58 — 固定 3 案例请求日志相关性回执（SAFE）

日期：2026-10-30。由 Owner 在 Mac 上运行私有工具并提供**仅含聚合计数的 JSON**。本助手未读取故事、消息 ID、私有 hash 或用户级数据库行。

| 固定来源 | 目标消息行存在/时间相符 | 终态事件候选 | 事件↔指标按 request_id 一对一 | 时间兼容候选 |
|---|---|---:|---:|---:|
| AUTHOR | PASS | 2 | 2 | 2 |
| CURRENT_PUBLIC | PASS | 5 | 5 | 5 |
| OLD_PUBLIC | PASS | 2 | 2 | 2 |
| **合计** | **3/3** | **9** | **9** | **9** |

Owner 报告 `R58_REQUEST_TIMELINE_CORRELATION_HOLD`。三组无超过 100 个候选的溢出、无缺失请求耗时；**任何一组都不能唯一识别目标消息对应的 API 请求**。`exact_request_id_join_between_logs=true` 仅代表 **事件日志 ↔ 延迟指标** 的 request_id 关联；`exact_target_message_to_request_join=false`。不能把时间兼容自动升级为直接请求关联。

固定源码 `sunxu/RolePlay@e9fe29c42434caeb0bac5acc91845ab4741ecb2b` 的 `V2ChatRequestEventService.record` 使用异步终态插入；`occurred_at` 不是已证明的真实请求开始时间。原 2 分钟前到 20 分钟后的宽窗口是候选搜索，不是可信请求匹配门禁。该源代码固定 SHA 也不等于已证明历史部署 SHA。

## 后续更有区分力的证据

1. **直接关联字段优先**：对私有封存包的 target metadata 做**仅键名布尔存在性**检查，不打印值。新增 `inventory_priority3_request_keys.py` 和 4 条纯合成测试。即使发现 `requestId`，也必须核对该字段的来源、写入语义与请求指标相同，而非仅比较字符串形式。
2. **独立软证据**：将候选 metrics 的 `token_breakdown.historyMsgCount=11` 与本轮确认的 11 消息条件窗口对照；将**目标 Assistant 自身**的 Ledger 完成更新时刻与候选终态时间做近邻分析。两者也可能重复，不能凭某一个软匹配消除 HOLD。
3. **请求级硬证据**：若原始请求日志或持久化元数据没有目标 message UUID→request_id 的可信映射，应保持 `AS_OF_REQUEST_HOLD`，禁止通过人为缩窄窗口制造“唯一候选”。

数据库元数据只读检查发现 `v2_chat_messages.analytics_event_id` 但没有直接的 request_id 列或指向请求事件的外键；`chat_history_request_metrics` 是独立历史读取指标，不能仅凭名称假定它就是聊天生成请求的 direct join。真实数据的值没有通过连接器读取。

## 可执行的离线下一步

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
python3 -m unittest discover -s experiments/r58_roleplay_replay \
  -p 'test_inventory_priority3_request_keys.py' -v \
&& python3 experiments/r58_roleplay_replay/inventory_priority3_request_keys.py \
  --private-dir "$HOME/.storyforge-r58-private/priority3_source_20261030_first_capture"
```

只需提交脚本输出的 SAFE JSON。它不访问数据库、不做任何写入，不打印目标元数据的值；训练准入 `HOLD` 不变。当前 Skill v0.1 未修改，PR #7 继续 Draft。

## Owner 本地目标 metadata 请求键检查结果

Owner 提供 `R58_LOCAL_REQUEST_KEY_INVENTORY_COMPLETE__DIRECT_LINK_HOLD`。对 `AUTHOR`、`CURRENT_PUBLIC`、`OLD_PUBLIC` 三条目标回复，各检查 7 种**顶层**预定义键（`requestId`、`request_id`、`apiRequestId`、`api_request_id`、`analyticsEventId`、`analytics_event_id`、`relayRequestId`），**共 21 个存在性结果均为 false**。这是确定的 Owner 本地安全诊断结果，但并没有扫描每个嵌套 metadata、数据库其他列、其他遥测表；不能断言绝对没有任何历史请求关联途径。源包、Prompt 与训练准入均未修改。

## 下一步：仅增加独立的候选软信号

已扩充原 `audit_priority3_request_timeline.py`，附加三项**不含私有标识的聚合计数**：

- `events_with_history11_metric`：同 request_id 的唯一延迟指标包含 `token_breakdown.historyMsgCount=11`；
- `events_near_target_ledger_update`：候选请求终态时间与**目标 Assistant 行**的 `update_after` Ledger 事件时间相差不超过 2 分钟；
- `events_with_both_soft_signals`：同时具备两项软信号，并且保留先前的 duration/time 兼容检查。

这些条件不会自动建立 target message ID 到 request ID 的直接键关系，也可能剩下多个或者零个候选；不能人为调窄窗口声称 exact。原 11 项合成测试扩大为 **15 项**，当前 Owner 尚未运行新测试与实际聚合查询。

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
python3 -m unittest discover -s experiments/r58_roleplay_replay \
  -p 'test_audit_priority3_request_timeline.py' -v
```

测试通过后，在已确认的专用只读 PG 环境重复运行既有工具（先 `--plan-only`、再不带该参数）；只分享安全聚合 JSON。强制保留 `exact_target_message_to_request_join=false`、`request_start_time_certified=false`、`provider_request_byte_exact=HOLD` 与训练准入 HOLD。

固定源码 `RolePlay@e9fe29c` 中 `historyMsgCount` 来自 `llmHistory.length`；当前数据库 `v2_chat_messages.analytics_event_id` 列存在但没有在已检查的持久化路径中确认它能指向请求 ID，因此不能作为直接关联证据。
