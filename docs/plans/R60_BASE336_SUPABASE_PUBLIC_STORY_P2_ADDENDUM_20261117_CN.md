# R60 Base336：Supabase 公开故事来源 P2 补充决策（2026-11-17）

## 状态

**P2_PROMPT_DRAFT_48_READY__WORLD_COMPONENT_CROSSWALK_PENDING**

本文件是对 `R60_BASE336_POST_TRAIN_QUALITY_EVALUATION_20261117_CN.md` 第 6、7 节的来源路线补充，不覆盖原计划的独立性、六维质量、盲审或训练授权门禁。

Owner 已明确批准：本轮以 Supabase 作为主要新来源，采用“仅公开故事与公开世界设定，构造全新评估提示，不读取用户私有会话正文”的路线。

授权范围仅为**内部独立评估提示构造**。不据此推断作者授予训练、公开发布或再分发权利；不把这些内容加入训练集。

## 1. Base336 时间边界

- Base336 探索性数据发布/冻结时间：2026-11-16 02:03:25 UTC。
- Base336 GPU Run 开始时间：2026-11-17 05:56:22 UTC。
- 入选来源均在 Base336 数据发布/冻结时间之后创建，因此记录级来源不属于该次 293/43 冻结数据包。
- 其中 3 条在 GPU Run 开始前创建，5 条在 GPU Run 开始后创建。

时间边界可证明这些故事记录晚于 Base336 数据包；**不能单独证明它们与 Base336 既有世界组件在语义上完全隔离**。

## 2. Supabase 来源筛选

只读取公开故事来源字段及审核/权限元数据。候选筛选条件：

- `visibility = public`
- `status = published`
- `deleted_at IS NULL`
- `moderation_state IN (ai_approved, human_approved)`
- `source_type = original`
- `public_v2_data.cardType = story`
- `public_v2_data.opening.originality = original`
- `public_v2_data.opening.visibility = 公开`
- `created_at >= 2026-11-16T02:03:25Z`
- 对发布冻结时间之前的公开原创故事执行 `public_v2_data.world` 精确 JSON 去重。

筛选结果：

| 项目 | 数量 |
|---|---:|
| 入选公开故事 | 8 |
| 故事谱系 | 8 |
| 作者 | 5 |
| 入选故事的不同 World JSON | 8 |
| Base336 GPU Run 开始前创建 | 3 |
| Base336 GPU Run 开始后创建 | 5 |
| 公开来源审核快照完整性通过 | 8/8 |
| 最新权限事件绑定最新审核提交 | 8/8 |

另有 1 条公开原创故事因可用世界/角色信息过少，不进入本轮平衡提示集。它不被判为质量失败，只是不满足本轮来源构造条件。

精确 JSON 去重未发现与冻结时间前公开原创故事的重复 World JSON。该结论只代表精确 JSON 不重复，不代表语义世界图不重叠。

## 3. 来源版本与权限核验

8 条入选来源均通过以下只读核验：

1. `public_content_revision` 与最新审核提交的 `content_revision` 一致。
2. 最新审核快照中的 `snapshot.source.v2Data` 与当前公开 `public_v2_data` 完全一致。
3. 审核快照内的 `contentHash` 与审核提交的 SHA256 一致。
4. 最新权限事件绑定到最新审核提交，目标可见性为 public。

SHA256 的作用域是包含 `source.v2Data` 的审核快照；不把它描述成只对 `public_v2_data` 计算的 SHA256。数据库中的 32 位 `public_content_hash` 仅作为不透明字段保留，不推断其算法或覆盖范围。

公开发布状态与 AI/审核批准记录用于确认本轮来源版本和公开状态；它们不被解释为作者授予通用模型训练权利。当前用户授权只覆盖本轮内部评估提示构造。

## 4. 新构造提示集

已在 Owner 私有工作区生成 P2 草案包，不提交公开仓库，不写入 Supabase：

- 48 条全新提示。
- 8 个来源，每个来源 6 条。
- 每个来源分别覆盖冻结 Quality-v1 六个维度各 1 条：
  - `chinese_prose`
  - `character_consistency`
  - `npc_initiative`
  - `player_agency`
  - `rule_fidelity`
  - `narrative_continuity`
- 每条提示严格包含 3 条构造消息：`user / assistant / user`。
- 三条消息均为新构造上下文，不伪装成历史持久化消息。
- 不含 System 消息、目标答案或参考答案。
- 上下文只改写公开世界/角色/开场信息；不把隐藏 director/system-like 指令作为模型输入。

六维门槛继续复用 `experiments/r58_quality/quality_v1.py` 中既有规则：4/4/3/4/4/4；严重标记仍为 `serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion`。

重要边界：该文件是**生成评估提示包**，不是 Quality-v1 SFT 候选 JSONL。不得把 Base/Adapter 生成回复送入 `quality_v1.py` 的源候选 `decide/summarize`，不得向 Gold Manifest 追加合成评估事件。

## 5. 未访问与未执行事项

- 未读取用户私有会话正文；未从 `v2_chat_messages` 提取私有消息内容。
- 未读取或访问 R50 密封测试内容。
- 未将 293/43 内容复制进新提示。
- 未修改 Supabase。
- 未启动 GPU、未提交 HF Job、未运行 Base/Adapter 推理。
- 未实现正式 Pairer、Backend 或 Profile。
- `quality_v1_admitted = 0`，`train_admitted = 0`，`model_promoted = false)。

## 6. P2 剩余门禁

当前仍不得冻结为独立 Held-out。正式 P2 PASS 前还需：

1. 将 8 个来源的 World 组件与 Base336 293/43 私有来源清单、已知 Protected/Reserved World 元数据做交叉核验；仅有不同 MD5 不足以证明语义隔离。
2. 对 48 条提示执行来源忠实性、无原文长段复用、无未来信息泄漏、无隐藏指令混入的独立复核。
3. 确认作者/平台权利范围仅覆盖获批的内部评估用途；不得扩大为训练或再分发。
4. Owner 冻结最终来源 Manifest、提示 SHA256 和世界组件隔离证据。

若无法取得完整的世界组件交叉核验证据，对应来源保持 HOLD；不得通过改名、重算 MD5 或仅凭时间戳宣布语义隔离 PASS。

P2 通过后，才按原计划进入 P3 的版本化薄适配器与合成测试。P4 Base/Adapter GPU 配对推理仍需单独、明确的 Owner 授权。
