# StoryForge R60 Base336 → P2 Quality-v1：新 Agent 唯一现行接手任务书与启动提示词（2026-11-19）

## 2026-11-20 P2-C 第一份外部独立语义审阅报告：8/8 模板独立意见（Owner 验证仍待）

**证据类型：Owner 在本次会话转交的一份独立 Reviewer 文字报告，不是由仓库程序自动生成的签署 SAFE。** 报告称以此前 Owner 0600、10,276,892 字节的 `R60_BASE336_P2_SOURCE_EVIDENCE_PRIVATE.json` 为唯一输入，涵盖 P2 8 Story、Base336 172 Story、当前 172 + 历史 203 = **375 来源版本**；其方法为四字段全文建索引、P2 专名（人物/别名/地点/组织/事件/规则）逐项检索、按题材近邻提取部分原文复核，全部 172 故事的索引档案经过查看。

- **逐 P2 来源自报判决**：`INDEPENDENT_TEMPLATE_ONLY=8`、`SAME_SEMANTIC_COMPONENT=0`、`INSUFFICIENT_EVIDENCE=0`；认为所见匹配仅是通用的职业/婚恋/校园/仙侠/贵族等题材原型，未发现具识别性的共用角色/世界/事件/剧情组件。**可将“P2↔Base336 首份独立语义意见已收到、8/8 给出方向性裁决”标为完成**，不再让 Reviewer 重新索引全部 375 份资料。
- **证据签收与覆盖精度仍限定**：Reviewer 自述“未接触原训练来源/其他 Reviewer 的结论”应理解为**独立审前未接触**，因为他确实阅读了本次提供的 Base336 来源证据。报告目前通过对话传达，未收到 Owner-local 原始**不可改动报告文件的 SHA-256、Reviewer 会话/交付身份核验、Review 所用确切证据包字节 SHA**；报告引用大量“B + 角色名”，**没有全部使用 Bxxx-CURRENT/Vnnn 可自动绑定的匿名版本引用**。文本索引覆盖 375 份数据≠每份原文全部通读，也≠ 8×375=3000 对逐对全文比较。为保证可复核性，Owner 应**只向同一位 Reviewer 请求最小补充**：审阅包版本/摘要确认、Reviewer 独立审前访问声明的精确定义、每个 P 来源负例检索的字段/版本覆盖计数及题材近邻的 `Bxxx-CURRENT/Vnnn` 版本引文；不可凭现在的自由文本报告把 Owner 技术签署改为 PASS。
- **单独数据质量风险**：Reviewer 发现 **1/8 P2 公开来源** 的 World/角色内容存在家族名或角色名改名残留，属于**候选题目自身规则/角色一致性瑕疵**，非 P2↔Base336 同源的直接证据。Owner 不得静默修正已绑定公开 revision 或直接丢掉六条问题；在正式 48 题冻结前应作私有源版本质量仲裁，并预设保留/剔除该来源的**成对模型评分敏感性分析**，避免把自相矛盾的原始提示当模型失误。
- **不重复开发/不重复抽样**：正式状态 `P2_BASE336_SEMANTIC_REVIEWER_1=8_INDEPENDENT_TEMPLATE_ONLY__OWNER_SOURCE_AND_INDEPENDENCE_PENDING`。它只覆盖 P2 vs Base336，不覆盖 R50 五世界以外完整 Protected/Reserved/Dev/Teacher 来源及历史 R47/48/55 的全部暴露，也不证明任何 historical actual-sent prompt 字节。**`reviewer_independence_verified=false`、`world_component_isolation_verified=false`、`historical_actual_sent_verified=false`、`r50_complete_exclusion_verified=false`、`P2_C=HOLD`、`P2_B_48_PROMPTS=NOT_GENERATED`、`quality_v1_admitted=0`、`model_promoted=false`**。
- **最短下游动作**：Owner 对独立 Reviewer 所用证据包和原始报告分别做本地只读 SHA + 0600 交付保全，获得对**版本锚及独立审前状态**的最小补充回执；这不是第二轮全量语义审阅。同时并行推进尚缺的 R50 以外 Protected/Reserved/Dev/Teacher 全集边界和历史请求 actual-sent 证明，不再重查 336/172/375 或 Gold48 的文本重复。

---

## 2026-11-20 Owner 最新真实回执：全 172 Base336 Story / 375 来源版本直接核验完成（覆盖本文件此前“134 个来源仍缺失”的历史阻塞）

**这是新的事实性门禁进展，不是自动 P2-C 语义隔离 PASS。** Owner 已使用现有脚本 `experiments/r58_quality/r60_base336_p2_source_evidence_capture_cpu.py`，配合刚生成的**新 2-before / 6-after、7 作者** P2 v2 私有 Manifest、冻结六目录和既有只读数据库连接，先运行无 DB 预检，再 `--execute` 成功：

- **无 DB 预检**：`P2_BASE336_SOURCE_EVIDENCE_PRECHECK__NO_DB`；冻结原始候选 336、真实来源 Story **172**、P2 8，Story ID 精确交集 **0**；未创建私有文件。
- **真实只读 DB 来源提取**：`P2_BASE336_SOURCE_EVIDENCE_CAPTURED__SEMANTIC_REVIEW_REQUIRED`；`base336_cases=336`、`base336_case_source_bindings=336`、`base336_story_ids=172`；冻结来源当前记录 **172**、历史归档版本 **203**，**375** 份来源记录的 `world/character/characters/opening` 各字段有值 **375/375**。
- 新 P2 八来源：`p2_snapshot_bindings=8`、`p2_permission_bindings=8`、`p2_manifest_binding_rows_verified=true`，四类字段均 **8/8** 有值。新来源对完整 172 Story 身份交集 **0**，对 **375 份**已抓取来源版本的 `world`、`character`、`characters`、`opening` **每个完整 JSON 字段的 exact matching 均为 0 P2 Stories、0 Base336 Stories、0 Record Pairs**。
- 以 `O_EXCL` create-only 已写出 Owner Mac 私有 `R60_BASE336_P2_SOURCE_EVIDENCE_PRIVATE.json`，大小 **10,276,892 bytes**；内容含冻结 336 case→Story/Session/Message 的原始来源关联、172 Story 的当前/历史组件、八个新的 P2 审核快照组件以及精确比较证据。**只保存 Owner Mac 权限 0600 的路径**，不上传 GitHub/CI、不公开正文、映射、SHA 或用户 ID；`database_modified=false`、`gpu_started=false`、`hf_jobs_submitted=0`、`model_requests=0`。
- **纠正本文件更早的旧状态**：现有 P2 × Base336 **全部 172 Story 身份和 current+archived 375 records 的来源捕获与精确字段交叉已完成**。不得再声称“134 Source ID/版本权威名单缺失”或要求 Owner 重跑旧提取脚本；早先 38 Story/59 records 子集证据仍可留存，但现由完整 172/375 证据覆盖其精确隔离范围。
- **仍明确 HOLD 的实质缺口**：`historical_actual_sent_verified=false`；`semantic_world_alias_verified=false`；`world_component_isolation_verified=false`；`r50_complete_exclusion_verified=false`；`reviewer_independence_verified=false`。整套来源字段精确不相等**不代表角色别名、人物关系、派系、事件、规则、世界观和情节语义独立**；实际发送到模型的 source revision/System/Rules 字节仍未得到证明，R50 五世界之外和其他 Protected/Reserved、Dev/Teacher 全历史集合的穷尽性也尚未封闭。现有 `src/storyforge_dataset/world_isolation.py` 只对**Reviewer 已声明**的 component IDs 验证分组冲突，不自行推断文本语义，不能误充独立判断。
- **下一唯一主线交付**：从**已生成的这一个 10.3MB Owner 私有证据包**对 P2 8 vs Base336 172 current + 203 archived 做独立来源语义审阅；Reviewer 必须实际查看真实 `world/character/characters/opening`、角色别名/世界规则/组织关系/事件与共享剧情，不得仅按 JSON MD5、字数或创建时间判 PASS。按每个 P2 来源保存完整覆盖范围、来源引文、版本/对应记录、具体同源或异源推理及 `SAME_COMPONENT / INDEPENDENT_TEMPLATE / INSUFFICIENT_EVIDENCE` 意见，任何证据不足保留 HOLD；每位 Reviewer 的独立性和私人交付字节由 Owner 验证，不把未签署评论当成正式独立审核。继续独立完成 R50 外 Protected/Reserved + 历史 Dev/Teacher provenance-only 全集覆盖、历史 request-effective 实际输入核验；仅全通过并 Owner 明确冻结后才能生成正式 48 Prompt + 48 Original Reference 并做四模型+原始答案同题六维盲评。
- **正式状态保持**：`P2_C=HOLD`、`P2_B_48_PROMPTS=NOT_GENERATED`、`ACTUAL_SENT_PROMPT_BYTES=UNVERIFIED`、`quality_v1_admitted=0`、`train_admitted=0`、`model_promoted=false`。不得重复数据抽取、自动运行 GPU/模型或通过 CI 代替人的语义裁决。

---

## 2026-11-20 来源冻结接口阻塞已修：仅最小向后兼容适配，Owner Freeze 仍待执行

**本项仅修复已知的 CLI/Manifest 接口不兼容，不重复选择 Gold、不新建通用提取器、不自动晋升 P2-C。** 当前 PR 已为既有 `r60_base336_p2_public_source_inventory_cpu.py` 增加可选 `--source-first-ids-file`，其旧默认 **3 before + 5 after / 5 authors** 源选择、v1 输出格式不变；新方式从严格 Gold48 source-first 审核已经确认的八个 Story UUID 读取**Owner 自有 0600 输入文件**，在数据库公开审核元数据中重新绑定 **2 before + 6 after / 7 authors**，限制创建时间不晚于 `2026-11-19T15:30:00Z`，输出新 v2 私有 Manifest，且 `owner_freeze=PENDING`。既有 `r60_base336_p2_source_evidence_capture_cpu.py` 已向后兼容 v1/v2、固定 count/schema/选择模式/输入源清单 SHA 形状，继续做来源修订与授权行精确比对，**不会因为版本升级而绕过旧门禁**。相关 P2 合成用例和全部 CI 必须通过。

**仅限 Owner 私有环境的操作合同**：将既有严格 Gold48 source-first 八来源 ID 按私有顺序写入权限 **0600** 文件；不得把普通按创建时间前八名、先前 Owner 原八来源、R50 sealed 或任何推测 Story ID 混入。该文件形状为：

```json
{
  "schema": "storyforge_r60_p2_gold48_source_ids_private_v1",
  "status": "GOLD48_COMPLETE_HISTORY_SOURCE_IDS__OWNER_FREEZE_PENDING",
  "source_selection_mode": "gold48_historical_full_prefix_source_first_v1",
  "story_ids": ["8 个经严格 Gold48 资格审核的规范 UUID 字符串；此处仅为格式说明"]
}
```

真实 `story_ids` 必须是**恰好 8 个独立数组元素**，上述说明文字不是有效输入。直接复用已有 `~/.local/share/storyforge/r60/private` 权限为 0700 的私有根目录，生成**不存在的** 0700 子输出目录；在本仓库执行：

```bash
BASE="$HOME/.local/share/storyforge/r60/private"
IDS="$BASE/p2-gold48-strict-eight-owner-private.json"
OUT="$BASE/p2-gold48-source-first-v2-20261120"
# Owner-only 预先写入 IDS（0600，8 个真实规范 UUID）；不在 shell argv 或公开 PR 中传 ID
test "$(stat -f '%Lp' "$IDS" 2>/dev/null || stat -c '%a' "$IDS")" = "600" || exit 1
install -d -m 700 "$OUT"
PYTHONPATH="$PWD/experiments/r58_quality:$PWD/src:$PWD/scripts:$PWD" \
python3 experiments/r58_quality/r60_base336_p2_public_source_inventory_cpu.py \
  --source-first-ids-file "$IDS" --output-dir "$OUT" --execute
```

输出的 `R60_P2_PUBLIC_STORY_SOURCE_MANIFEST_PRIVATE.json` 仍是**候选元数据证据包**，不是 Owner 正式不可变冻结、Gold48 具体 48 对内容的冻结、P2-C 语义独立 PASS 或真实历史 actual-sent 原文证明。确认 4 保留/4 新增、已核验公开许可在首条合格历史 Gold 之前生效之后，再用已有 `r60_base336_p2_source_evidence_capture_cpu.py` 及 Owner 六个冻结历史目录建立剩余 134 Source 绑定；旧版本 v1 manifest 和旧任务不变。**禁止在公开 GitHub 提交新私有 manifest、原始 Story ID、Session/Request ID 或聊天正文。**

---
 
## 2026-11-20 最新执行结论：Gold48 历史请求链路实测；新模型质量比较仍为唯一主线

**本节优先于下方 2026-11-19 的“固定三消息/新造 48 题”“只允许读取公开卡而不能验证聊天”的过时操作步骤；不改变旧冻结训练集、不自动使 P2-C PASS。** Owner 已再次明确授权真实聊天用于本项目**内部独立模型质量评估**；无需再要求重复提交授权证明。现有 SQL 仅返回 SAFE 聚合；不得在公开 GitHub 发布私人会话正文、ID 对应表或请求 trace。没有另行授权训练、付费 GPU/HF 推理、对外分发或 R50 sealed 正文访问。

### 已完成的真实新证据（不可重复做成“新进度”）

1. 固定新来源候选创建时间为 `2026-11-16T02:03:25Z` 至 `2026-11-19T15:30:00Z`：**17 个**公开原创 Story；实时池后增 1 个到 18，不能混入本次固定范围。采用已存在的公开审核快照/revision/许可事件合同，严格完整历史筛选后可用的**临时**来源是 **8 Story / 7 作者 / 8 个不同 World JSON / GPU 前 2 + 后 6**；与先前 Owner 批准的公开元数据原 8（3/5）**不相等**，替换来源还未正式 Owner Freeze。不得声称 2/6 新来源已在旧 Manifest 中冻结。
2. 固定三消息 `user/assistant/user` 不是历史原始模型 Prompt：上一轮 48 候选中 21 条有更早消息。全部 17 来源中完整历史恰好三消息的候选仅 **32**，每 Story 最多 5。**不能继续以 8×6 固定三消息构造 Gold 对照**。
3. 改为每条原始 Gold 之前的**完整持久化 role/content 前缀**，目标非空、`completed`、`finishReason=stop`；前缀中无缺失/非完成 Assistant，首条不早于当前公开卡版本生效时点，最高 40 消息/24,000 字符；只接受公开卡审批绑定通过的来源。额外排除发现的事后删除早轮次消息风险（**8** 个候选）、完成版正文历史差异风险（**4** 个候选）、编辑标记及晚创建前文。在所查范围 **320** 个基本候选中有 **308** 个通过这些历史一致性屏。跨会话精确去重 Prompt 和 Gold 后，在上述临时 8 Story 各取 6，得到 **48/48 不同完整历史 Prompt + 48/48 不同真实原始 Assistant 答案**，覆盖 **25 个历史 Session**，最长所选历史 **13** 条消息。这证明候选容量和可见历史完整性，**不是 48 个独立会话、六维审核或原始实际发送字节 PASS**。
4. **真实请求证据链已找到，勿再盲查空表 `v2_chat_reply_jobs`：** 新范围会话的 `chat_latency_metrics` 有 **1,361** 条请求计量，全部在 `v2_chat_request_events` 以相同 request_id 且相同 Story/Session 一一找到事件。两表无已发送 Prompt 原文，但计量有 `token_breakdown.historyMsgCount`、System/History/Input Token 数与请求结束原因。
5. 对前项经过删除/编辑/正文差异排除且全前缀去重的 48 Gold，在 **同一 Story/Session、±5 分钟、HTTP 200、`historyMsgCount == 数据库完整前缀消息数`** 条件下，**48/48** 都找到**唯一一条成功请求记录**；匹配的 48 个 request_id **互不相同**，**48/48** `finishReason=stop`、System/History/Input Token 计数均非零；**47/48** 时间差不超过 2 分钟、48/48 不超过 5 分钟。仅按“时间最近”会错配（45/48 历史数量吻合），所以必须采用联合绑定；**这仍只证明请求存在、历史消息数及请求计量一致，未还原当时 System/World/Character/Rules 字节、具体历史消息字节是否全部发送及模板/截断。**
6. 直接在只读数据库对上述固定 17 新来源与 Base336 截止 `2026-11-16T02:03:25Z` 前的 **5,436** 条当前/ **6,977** 条存档来源 World/Character/Opening 完整字段比较：**精确完整字段复用命中 0**。WorldSentence 长度至少 16 的新来源有 15 个，与旧 8,332 条长文本所做 `pg_trgm` 非独立预筛，最高相似度 **0.092**、0.45 以上命中 **0**；另 2 个新来源文字过短不能作有效相似性证明。**这只排除覆盖范围内的确切文本复用及明显近似世界句子，不能将其升级为完整角色/事件/世界语义、历史 Dev/Protected/Reserved/Teacher 全集独立性 PASS。**

### 2026-11-20 实际新证据：Historical Original Reference 的模型来源（盲评后分层）

- `ai_model_pool_attempt_metrics` 是 48 条 Gold 对应的实际模型调用尝试日志。以本阶段已验证的唯一成功请求映射（相同 Story/Session、±5 分钟、HTTP 200、`token_breakdown.historyMsgCount` 与持久化历史前缀数一致）为输入，再按 `logical_request_id` 关联实际模型尝试。**48/48** 个 Gold 目标都有模型尝试与成功结束（HTTP 200 / `finish_reason=stop`）记录，48 个 request ID 仍互异。实际生效模型分布为：`cl-gemini-3.8-flash-high` **26**、`cl-gemini-3-flash` **21**、`cn-deepseek-v4-flash` **1**。这些只是提供方平台的 effective_model **标识**，不证明底层模型确切二进制/revision，也不证明原始 Prompt 字节。
- **不得把原始 Gold 称作人工金标或客观正确答案**：它是不同在线生成模型当时实际产生、已持久化的 **Historical Original Reference（历史原始回答基准）**。Quality-v1 六维分数必须对每种来源以同一打分规则独立评判。五来源同题盲评的 Reviewer 不得看到 Gold 来源身份或其有效模型；**Owner 解盲后**在总体 Base336 vs Historical Original Reference 对照之外，应按原回复实际有效模型分层汇报，注意 1 条 DeepSeek 子层不足以单独作统计结论；不要把历史模型混合带来的水平差异误判为训练效果。
- 新查数据库中的 `v2_generation_evidence_request_links` / `v2_generation_evidence_grant_operations` 各有 2 行，但与本次固定来源会话关联的请求证据 link **0**。相关 `ai_model_pool_attempt_metrics` 的请求尝试能提供 provider/model/finish reason/token 信息，**没有发送 Prompt 原文**；`ACTUAL_SENT_PROMPT_BYTES=UNVERIFIED` 仍然严格 HOLD。
- 针对固定 17 新来源中同作者历史复用风险，旧同作者有 143 个 Story / 1,016 份当前及归档版本关联；新旧主要角色姓名完整重复 **0**、长度足够的成长背景/人物介绍/开场完整字段重复 **0**，相关四类字段的 pg_trgm 相似度均未达到 0.30（最高 world 0.094）。**此项是有限的同作者文本隔离预筛，而非经独立 Reviewer 审定的剧情/角色组件语义 PASS**。别名、隐性情节复用、Protected/Dev/Teacher 全集交集仍需核查。

### 2026-11-20 新增独立来源子集的真实私有冻结证据：冻结 38 Story/59 版本直接 P2 隔离核验

- **已复用 Owner 先前提供的私有冻结清单** `R60_BASE336_WORLD_CROSS_SPLIT_REVIEW_PRIVATE.json`，而非重新从 Story 创建时间推断训练集合。其 Schema 为 `storyforge_r60_base336_world_cross_split_review_private_v1`，约束是 Base336 冻结 336 case/172 Story 中 8 个跨 Train/Validation 精确 World 组，**38 个不同冻结 Story（28 Train/10 Validation）**，清单组成员出现次数 40 但跨组去重后 38。**这不是完整 172 Story roster。**
- 不向日志/PR 输出清单中的任何 Story ID、Revision ID、人物名、正文或私有 SHA；只在只读 SQL 内用私有 ID 执行精准绑定。数据库 `user_stories` **38/38** 精确身份找回；清单点名的 `story_content_versions.id` **21/21** 归档修订精确定位、对应作者匹配、版本源时间早于 `2026-11-16T02:03:25Z`。取得的是 **38 当前 + 21 精确归档 = 59 份 source/version**，而不只是宽口径抽取的全部旧版本。
- 本次固定创建截止的 17 个新公开 Story 对这 38 冻结 Story 的 **Story ID 交集=0、作者交集=0、World/Character/Opening 整体字段精确重用=0**；对上述 **59 份版本**做跨来源主要角色姓名（主角色及 characters[0]）、World JSON、Character、Characters、Opening 组件相等比较，命中 **0**。将世界句子、开场、人物介绍与成长背景文本分别做 `pg_trgm` 预筛，新 17 个来源中四字段任何一个最大相似度达到 0.30 的 Story 数 **0**（最高世界 0.053、开场 0.022、介绍 0.027、背景 0.035）。
- **裁决范围必须严格限定**：`P2_C_BASE336_FROZEN_CROSSWORLD_38_STORY_59_VERSION_EXACT_AND_TRIGRAM_SCREEN=PASS_PRELIMINARY`，表明这个明确已知冻结来源**子集**的精确身份、作者及可见文本重复/明显相似风险排除成功；**不代表独立 Reviewer 的最终语义结论**，并且 **172-38=134** 个 Base336 冻结 Story 没有此项 source-bound 审核；R50 五世界以外、其他 Protected/Reserved、旧 Dev/Teacher/仲裁和完整模型请求组装仍 HOLD。私有 roster 自身声明 `semantic_review_completed=false`、`actual_sent_version_verified=false`，不能改写。
- **下一唯一有意义动作**：找出已存在的 Base336 最终 293/43 发布输入对应**剩余 134 个 Story 的权威 metadata/version**（不得再次构造通用工具或用宽口径“全部旧表记录”冒充冻结名单），再仅对仍未覆盖集合进行来源 ID、作者、角色/剧情/世界组件与历史暴露边界核验；其后才可以安排独立 Reviewer 对临时 2/6 八来源的真正语义裁决。Gold48 候选及已完成的 48 唯一历史请求链路不得反复重测。
- `P2_C=HOLD`；`P2_B_48_PROMPTS=NOT_GENERATED`；`ACTUAL_SENT_PROMPT_BYTES=UNVERIFIED`；`MODEL_PROMOTED=false`，不启 GPU/HF。

### 2026-11-20 Owner 原始 P2 八来源与严格候选八来源：4 保留、4 替换（权威私有清单真实比对）

- 在内部读取 Owner 先前上传的 `R60_P2_PUBLIC_STORY_SOURCE_MANIFEST_PRIVATE.json`（`storyforge_r60_base336_p2_public_source_inventory_private_v1`，原始 **8** 个来源）作为**唯一旧冻结名单**，并与 DB 固定 `2026-11-16T02:03:25Z..2026-11-19T15:30:00Z` 范围内通过**历史完整前缀、正常完成、无显式编辑、无已完成快照变化、无历史事后删除、公开版本/许可精确绑定且每来源至少六条合格 Gold 结构**的八来源做**私有 Story ID 交集**：旧冻结 **8**，新合格 **8**，**交集 4、原有但不合格 4、新合格但不在旧冻结 4**。新增四个创建于 Base336 GPU 开始之后。
- **纠偏：之前“保留 5、替换 3”的暂定策略已被本项准确的 Owner 私有名单比对推翻。** 当前实际 P2 来源需要 **4 个替换来源**的 Owner 私有 create-only 冻结与独立语义审核；不得沿用旧 3/5 八来源 Manifest、旧 5/3 预测或动态实时选源结果来伪称新八来源已冻结。后续必须重新核对每条新来源的原始请求、角色/剧情语义和历史暴露。没有输出任何 Story ID、个人身份或对应关系。
- 已检索目前可访问的用户文件库（2026-11-01 至 20 的完整目录元数据、相关已上传的 R60 私有来源文件、R60 历史证据 ZIP）以及已连接的 Hugging Face 只读模型/数据集仓库与既有 Jobs：未找到 **Base336 最终 293/43 训练输入或 336 case/172 Story 完整冻结名单**。已发现的 `R60_BASE336_WORLD_CROSS_SPLIT_REVIEW_PRIVATE.json` 是权威但**只有 38 个 Story（21 个指定归档版本）**；22-case 私有 HOLD 范围是这 38 个的一部分，不是新的来源；R57/GOLD 历史暴露文件也不是 Base336 release roster。**没有证据可合法把其余 134 个 Story 作为完整冻结来源凭空推断。**
- 仓库现有 `experiments/r58_quality/r60_base336_p2_source_evidence_capture_cpu.py` **正是需要复用的 Owner-local 172-source 读取入口**：基于既有冻结六目录、实际 336 cases、Owner P2 私有 Manifest 和只读 DB，create-only 在 Owner 私有 0600 路径保存来源-版本及八源组件证据，仅输出 SAFE 计数。目前 Owner 本机的真实发布数据与私有证据路径并未连接到本次会话运行环境，且先前执行因 `DB_BASE336_SOURCE_QUERY_HOLD` 未得到可用正式源包；**不重复开发，也不伪称运行成功**。这份脚本现有 `--p2-manifest` 是**旧八来源**，在四个新来源重冻并生成新的 Owner-only 八来源 Manifest 前，直接执行它也不能证明新八来源 P2-C PASS。
- 剩余的实际主线：**Owner 私有环境内对最终 release 数据和新八来源 Manifest 做最小范围 source-bound 绑定** → 只审剩余 **134 个**训练来源及 Protected/Reserved/Dev/Teacher 缺口 → Reviewer 真正独立裁决 → 同题完整历史 Prompt + Gold 48 条正式 Owner freeze → 四生成模型/历史原始 Gold 五来源六维盲评。无需重做已有 38 Story/59 来源版本、历史 48 成功请求或 R50 五世界。

### 2026-11-20 新增关键实测：R60 Base336 293/43 实际发布字节与 Gold48 直接曝光核验

- **新证据入口：已连接 Owner 有权访问的 Hugging Face 私有训练 Bucket**。原来只查模型、Dataset 仓库和目前账号可见 Jobs，未查到训练输入；本次经 Bucket 目录只读检索，确实在与 Base336 GPU Run `r60-base336-gpu-20261117T055622Z-b609cb78661d` 对应的预检 Stage 中定位 `train.jsonl`、`validation.jsonl` 和 `R60_BASE336_EXPLORATORY_MANIFEST_PRIVATE.json`，另有 GPU SAFE 回执（训练完成，`ckpt-37`，adapter reload/terminal PASS，not promoted）。
- 对 Stage 文件的原始 UTF-8 字节做只读分段 SHA-256 校验，**Train = 1,117,378 bytes / 293 rows，Validation = 151,105 bytes / 43 rows**，各自与 Manifest 的私有原始字节摘要 **完全相符**；**336/336** 行为 `user/assistant/user/assistant` 四消息结构。Manifest `status=EXPLORATORY_TRAIN_VAL_ONLY__NOT_FORMALLY_ADMITTED`，`train_admitted=0`，GPU 回执 `model_promoted=false`。不向公开 GitHub 输出 Bucket 具体私有 URI、训练正文或摘要。
- 发布 `train.jsonl` 和 `validation.jsonl` 的每行**只有 `messages` 字段，没有源 Story ID / Session ID / Revision ID**。这意味着它们并不能**单凭文件本身**恢复完整 172 来源的正式冻结 roster；但实际发布字节已经确切绑定，今后不能再称“完全找不到发布输入”。
- 以先前权威 Owner 私有 38 Story 跨 Split roster 为**精确、受限的原始来源集合**，只用现成数据库历史消息对实际 Train **293/293 条**做 exact Assistant Text + 同一 Session 连续前 3 条历史角色/正文完整匹配：**82 条 Train 样本完全四消息一致，恰好覆盖该 roster 的 38/38 Story，跨不同 Story 的歧义匹配 0**。先前实际 Validation 43 条对这 38 Story 的 Assistant 全文 exact 检查命中 0。**注意：0 条回答命中不自动证明 Validation 在 source-ID 层绝无这些 Story；这个结论只对可验证的 Train 82 条及完整 38 Story train 代表性有效。**
- 试图用完整 293/43 全文反推其余冻结 Story ID 的全球库匹配，在数据库 `EXPLAIN` 中须扫描估算约 **391 万**条 Assistant 消息（Postgres `v2_chat_messages` 全表估计约 780 万行），原文没有现成索引。**只做了 EXPLAIN，不执行高成本全库匹配或增加索引/数据库写入**。其余 **172 - 38 = 134 个冻结来源**仍需从 Owner 有来源标识的真实六目录/阶段 crosswalk 提取，复用现有 `r60_base336_p2_source_evidence_capture_cpu.py`，不可将发布脱敏 `messages` 本身视为身份 roster。
- 利用已有严格 P2 资格筛选的临时 **8 Story × 6 = 48 条完整历史 Prompt / 真实 Original Gold**，在数据库内仅获取真实核验必要的内部文本，与上述 SHA-256 完全验证的 Train293 + Validation43 逐字比对（所有实际源文本仅在受控工具运行中存在，未输出公开）。**Train 和 Validation 双侧分别均为：48 条原始 Gold 答案全文出现在任何单条训练消息的次数 0；Gold 与训练 Answer 完全一致 0；Gold 最近 3 条历史 Prompt 完全一致 0；四消息问答完全一致 0；Gold 最后 User Message 长度至少 30 字符时完全一致 0。** 即：`P2_GOLD48_VS_ACTUAL_BASE336_293_43_EXACT_TEXT_EXPOSURE=ZERO__PRELIMINARY`。这比时间/World JSON 非重叠更强，但**仍不证明语义隔离、训练源角色/剧情组件无改写、R47/R48/R55/R50/Teacher/Dev/Protected 全集未曝光或 historical actual-sent 请求原文字节**。
- 还直接以**Owner 原始 P2 八来源 Manifest**与临时严格八来源比对，确认**旧 4 保留 / 新 4 需替换**；按两组各 4 个做**历史首条合格 Gold 时间点前的授权生效核验**：**8/8** 审核 revision 与当前公开快照吻合、64 位 content hash 合同、Story/Submission/Permission 同作者、Submission 与 Permission 绑定、二者时间均不晚于其该故事首条合格 Gold、公开版本在当时已生效。新四来源该来源权利/版本子合同通过，**不是 Owner 已重新正式冻结**。
- **现有代码合同的精确阻塞**：`r60_base336_p2_public_source_inventory_cpu.py` 的 deterministic selector 固定取前 **3+5**，且 `validate_rows` 强制 **5 作者**；`r60_base336_p2_source_evidence_capture_cpu.py::load_p2_manifest` 也固定接受 **3+5/5 作者**。严格历史 Gold 的临时新八来源实际为 **2+6/7 作者**，且是 source-first 筛选，并非简单创建时间前 2/后 6。因此直接重跑旧 inventory/capture 无法证明新的八来源。**不要添加第二套新工具，不要静默更改旧冻结版本；只有在 Owner 私有环境确认八来源 create-only freeze 输入后，才对这些现有脚本做最小向后兼容的明确选源/计数合同适配并跑其原有 CI。**
- **门禁仍严格**：`P2_C=HOLD`、`P2_B_48_PROMPTS=NOT_GENERATED`、`ACTUAL_SENT_PROMPT_BYTES=UNVERIFIED`、`P2_NEW48_MATCHED_ORIGINAL_GOLD=UNVERIFIED_HOLD`、`quality_v1_admitted=0`、`model_promoted=false`。无新增模型请求、GPU/HF Jobs、数据库修改、代码通用抽取器；上述连读文件均为只读 Bucket/DB 聚合核验。
- **唯一新增信息的后续用途**：Owner-side 从 336 带 provenance 的构建六目录锁定缺失 134 Story + 新八来源 create-only 0600 Manifest → 才对剩余训练/保护/Dev/Teacher 组件做增量身份和独立 Reviewer 真正语义审查；同时真实历史请求原文若确实不存在，应按源输入限制明确实验合同，不允许拿 48 唯一 request 的 Token 元数据假装 actual-sent 字节；然后才可做 48 同题五来源 Quality-v1 六维盲评。

### 2026-11-20 最新增量核验：Gold48 × Base336 实际发布集近似文本筛查和会话聚类

- **仅针对已经 SHA-256 确认的实际 293/43 发布内容**：在先前完整字符串 exact 命中 0 基础上，对现有严格来源八 Story 的 **48 条独立最后 User 输入、48 条 Original Gold 回答**，分别与实际 Train293/Validation43 最后 User/Assistant 内容做 **NFKC、去标点空白、字符 5-gram Jaccard** 启发式预筛。每个 Gold 只报告对各 Split 的最大相似度，匹配用户原文与 Answer 均不公开。四组中相似度 >=0.20 / >=0.35 / >=0.50 / >=0.70 的 Gold 个数均为 **0**；最大值分别为：最后 User vs Train **0.012**、User vs Validation **0.002**、Gold Answer vs Train **0.023**、Gold Answer vs Validation **0.009**。因此 `P2_GOLD48_VS_ACTUAL_RELEASE_VERBATIM_AND_5GRAM_NEAR_DUPLICATE=ZERO_PRELIMINARY`，是**局部文本暴露排查**，不能替代改写/同源世界、隐性角色、历史 Protected/Dev/Teacher 或独立 Reviewer 语义核验。
- **48 题的统计非独立性**：严格来源 8 Story / **25 Session**；只含单题 Session **8**，含多题 Session **17**，**40/48** 条题目来自这些多题 Session，最多一 Session 六题；同一 Session 内可成对的评估题目 **35 对**。最后一条 User 文本为 **48/48 不同**；完整历史长度最少 3、最多 13 条消息，**23/48** 条包含超过三条前文。题目确实不同，但不可用独立同分布的 `n=48` 直接计算夸大的显著性或区间；**正式模型比较除了 48 题的成对六维逐题结果，还必须按 Session 聚类重采样/敏感性报告**（Story 级分层作为辅助），对有很少独立 Session 的小子组不要声称显著。
- HF 私有 `quality-review/r60` 下另有约 3.9MB 的旧评审 `source.private.jsonl`，抽查其行包含匿名 `blind_id`、`visible_history`、`target_text` 等，但**不含 Story ID / Session ID / Case 源身份**，不能冒充剩余 134 Base336 训练来源的真实交叉表。其他 Bucket 内已定位的实际 `train.jsonl` / `validation.jsonl` 也只有 `messages`。生产库泛化反向 join 需约 391 万 Assistant 消息 Seq Scan，已通过 `EXPLAIN` 拒绝执行；**不在生产上新增正文索引或全库扫查**。完整 172 来源仍只有 Owner-local 六目录/带身份构建产物能够给出权威版本。
- **正式实验口径固定**：五来源为真实 Original Reference（历史线上 26/21/1 三种 effective_model 混合）+ Qwen Base + R46 v0.2 ckpt7 + R54 v0.3-A ckpt16 + R60 Base336 ckpt37；本轮没有真实模型新回答，也未评分。继续六维题目级盲评，Owner 解盲后报告 Gold 来源模型分层和按 Session 聚类的 R60–Gold 成对差异；历史原始 System/World/Rules actual-sent 字节还没有锁定，需在评估合同中明示系统提示差异。**P2_C、P2_B 正式冻结、Reviewer 独立门禁仍 HOLD；已完成的 Gold48/38 Story 及 actual release 完整性不得再重做。**
- 下一轮执行优先级严格限定为 **新增四源 Owner-private create-only freeze** 与剩余 **134 个 Base336 Story 的 Owner-local authority crosswalk**，按身份和版本开展真正独立语义复核，然后才正式开展四生成模型 + Gold 五来源质量评估。既有 source capture CLI 需要六个历史冻结目录（`--old-dir --plan-dir --v2-dir --v3-dir --audit-dir --quarantine-dir`）、`--p2-manifest --output-dir --execute`；**旧 Manifest 接口仍固定 3/5、5 作者，当前严格 2/6、7 作者尚不兼容**，必须最小向后兼容适配，不能静默篡改旧冻结清单。

### 当前唯一最短下游动作

- **P2-C 剩余实际阻塞：** 为临时 2/6 新来源组合绑定有权威来源的 Base336 172 Story + 全版本角色/剧情语义、所有受保护/历史 Dev/Teacher 保留集合，做真正独立的新来源 Reviewer 裁决；只差未覆盖集合，不重审 R50 已闭合五世界、旧 R47/R48 20 题、Base336 老 10 条 Review 边。
- **Gold actual-sent 缺口：** 现有 request_id、System/History/Input Token 和前缀数已验证，但 **原始实际发送的完整模型请求内容未落在当前查过的表中**。下一步仅定位原始模型网关/请求组装记录的可信证据，或明确冻结一个**“历史持久化前缀下的原始 Gold 对比”**实验合同，并公开承认与原服务 System/Memory/Rules 并非已证明的完全同题输入；不能在未授权情形下凭当前公共卡伪造旧 request payload。
- **P2-B：** 新候选来源固定后再以真实完整历史 Prompt + 原始 Gold 为一体逐题冻结；Quality-v1 六维场景归类必须另审。原 `read_gold(expected_count=48)` 精确前缀检查可复用，但仅作来源匹配，不代替真正 request 字节证明。不得重造通用 Gold 抽取器，除非正式合同要求的最小适配确有必要。
- **P4/P5:** 仍以原始 Gold + Qwen Base + R46 v0.2 ckpt7 + R54 v0.3-A ckpt16 + R60 Base336 ckpt37 的**五来源同题匿名盲评**为目标；必须给出 `Base336 vs Gold`、`vs Base`、`vs v0.2` 和 `vs v0.3-A` 六维/严重缺陷结论，不能只比较生成速度、训练 loss 或 Token。
- **门禁不变：** `P2_C=HOLD`；`P2_B_48_PROMPTS=NOT_GENERATED`；`P2_NEW48_MATCHED_ORIGINAL_GOLD=UNVERIFIED_HOLD`；`quality_v1_admitted=0`；`model_promoted=false`。此处 `48/48` 指数据库来源/请求**候选容量**，不是 Owner-only 0600 正式字节冻结或真正独立质量评估 PASS。

SAFE 证据保留在现有 [PR #31](https://github.com/sunxu/storyforge/pull/31) 对话（2026-11-19T15:30Z 界限后的 Gold 完整历史核验、请求联合匹配与本节新事实）；真实来源/请求字节若取得只能留在 Owner 私有环境，不能在 GitHub 公开。

---


## 八、2026-11-19 Owner 新要求：原始回答 Gold 必须参加同题盲评

**本节是 Owner 明确提出的评估要求，优先于本文件前面“原始 Gold 不纳入新评估”的旧说法。** “Gold/原始回答”是**第五种回答来源**（冻结原始记录的 Assistant 回复），**不是第五个推理模型**。评估必须回答：训练后的 Base336 输出相比同题原始回答，在六维质量及硬错误上是提升、持平还是回退。

### 正式阵容与计数（待 P2-C / Gold 来源绑定及 Owner 冻结）

| 回答来源 | 类型 | 48 题对应数量 |
|---|---|---:|
| 冻结来源的原始 Assistant 回答（**Gold/reference**） | 现成的来源回复，**不运行生成** | 最多 48；目前新 P2 **尚未证实存在 48 份同题匹配原始回复** |
| Base Qwen 原版 | 模型生成 | 48 |
| R46 v0.2 checkpoint-7 | 模型生成，历史强基准 | 48 |
| R54 v0.3-A checkpoint-16 | 模型生成，诊断臂 | 48 |
| R60 Base336 checkpoint-37 | 模型生成，新训练主角 | 48 |

如果证据就绪，则为 **48 × 4 = 192 份新模型回答 + 48 份冻结原始回答 = 240 份待盲评文本**，不是 240 次模型生成。若预算限制，事先冻结三生成模型 Base + v0.2 + Base336，得到 **144 份模型回答 + 48 份 Gold = 192 份待盲评文本**。**Gold 不能随预算降级而删除**。

### 最重要的数据来源矛盾：不能用不相同的题硬凑 Gold

现行 P2 来源合同是 8 条公开 Story 的 **World/Character/Opening** 元数据，并在每条来源下**新构造六条** `user/assistant/user` 测试上下文。这些新提示**天然没有可证明的“历史原始回答”**。R48 的 Gold 属于旧 R47 20 题（2 Story、已曝光），不是新 48 题的答案；不能把 R48 Gold、公开 Opening、历史 Test 目标、模型代写或无来源的“标准回复”当作新 48 题的原始回答。

**在 P2-C 完成前，应把“原始回答可比性”增加为独立来源门禁**：
1. 先查已批准的 8 个 P2 来源是否**已有合法可用且未参与训练/旧曝光的原始回答与其完整前置 Prompt 上下文**，只核验存在性、权利和冻结 provenance，不访问用户私有会话正文，也不重新抽取已完成的 P2-A Inventory。
2. 若确有合法的新原始回复，必须由 Owner 在**私有空间**确定每个原始回答的 `source revision + cutoff/actual-sent context + final assistant turn`，并验证 `frozen prompt.messages == original_record.messages[:-1]` 的**逐消息 role/content 精确匹配**，`original_record.messages[-1].role == assistant` 且回答非空；参考已存在的 `scripts/v02_r48_four_arm_build.py::read_gold`，**复用合同、不要复制开发一套通用 Gold 提取器**。验证任何原始回复的出处、权限或训练/开发曝光是否不确定时维持 HOLD。
3. 如果 8 个来源只有公开 World/Opening、没有与新 48 提示相同的原始回复，必须明确给出 `P2_NEW48_MATCHED_ORIGINAL_GOLD=NOT_AVAILABLE`，而不是伪造参考答案。Owner 若坚持“正式盲评 48/48 都与原始回答比较”，需在**保留新世界独立性与用途权利**前提下，调整 P2-B 为**有独立原始回答的合法未曝光 Prompt/Gold 对**；可能需要另获授权、重新选择或创建参考回复，并明确这是新增作者/人工回答而**非历史原始回答**。在这项条件满足前，五回答来源正式报告不能声称完成。
4. 已冻结旧 R47/R48 的原始 Gold 可以**仅在完全相同旧 Prompt**上与新模型结果做**单独、明确标记 EXPOSED_DEV** 的回归比较；Base336 293/43 训练与 Validation 原始 target 也只可以单独做**受污染的训练/验证诊断**，绝不能与 P2 的新 Held-out 六维结果混算、补齐 Gold 或当做模型泛化证明。不要为了该补充任务重新跑旧 R48 盲审或打开 R50 密封材料。

### 盲审、审计与评分合同

- 在 Reviewer 所见逐题同一个 Prompt / World 证据框架下，把 **Gold 与所有模型输出完全同权匿名随机排列**（例如五份随机字母，不固定 Gold 的位置），Coordinator-only 0600 私有映射在 Reviewer 评分冻结后再解盲。
- **必须同时报告** `Base336 vs Gold`（Owner 本次核心要求）、`Base336 vs Base`、`Base336 vs v0.2`，有诊断臂时再报 `Base336 vs v0.3-A`；Gold 自身按六维与严重标记评分，**不是绝对正确、也不自动满分**。R48 旧 Gold 曾出现严重玩家自主权标记，不能把“接近 Gold 的文字相似度”冒充质量提高。
- 每题私有证据要分别绑定：原始回答字节/来源 SHA、对应 Prompt SHA、来源时间/版本、权限、是否被旧模型训练/开发曝光、所有模型生成哈希与 stop/truncation 状态；**reference answer 不得进入任何模型生成输入、模型工具链或公开评审包的身份栏**，只能以匿名回答形式进入盲审。
- 48 题属于 8 个来源 / 5 位作者，Reviewer 和模型回答只是重复观测；按来源世界聚类/分层报告并保留不确定性与三种 severe flags，不把 240 份回答当 240 个独立故事。
- 这项 Owner 要求更改的是未来评估合同，**不是授权读取任何私有对话或 R50 sealed 内容，更不是 GPU 运行授权**；不得为补 Gold 悄悄改变 P2 已批准的来源/用途范围。

**此刻状态**：`P2_C=HOLD`、`P2_B_48_PROMPTS=NOT_GENERATED`、`P2_NEW48_MATCHED_ORIGINAL_GOLD=UNVERIFIED_HOLD`、`P4_MODEL_REQUESTS=0`、`train_admitted=0`、`quality_v1_admitted=0`、`model_promoted=false`。新 Agent 要把 Gold 逐题绑定作为未来正式 5 份回答盲评的真实输入要求，而不是在源缺失时继续称“48 × 5 现成可评”。

---


## 七、2026-11-19 被评测模型阵容重新评估（取代本文件原先仅 Base/Adapter 两臂的默认设计）

**状态：建议的 preregistration 设计，尚未经 Owner 最终冻结，也不授权新的 GPU/HF 推理。** 本文件第 1 / 5 节原写的“Base/Adapter 两臂”仍是**最低主比较**，不应视为已获批准的最终模型阵容。历史 R50/R56 曾提出 Base/v0.1/v0.2/v0.3 四模型；R47/R48/R55 的真实结果表明应将“新 Base336 对比历史强 Adapter 与最新旧版本的回退”列入同一次新的独立质量评估。

### 推荐：4 个生成臂，分主比较和诊断比较

| 臂 | 冻结模型 | 本轮地位 | 历史证据理由 |
|---|---|---|---|
| A | `Qwen/Qwen3.8-27B` 原始 Base，revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` | **必须** | 校验本轮微调是否较 Base 获益 |
| B | R46 **v0.2 checkpoint-7** Adapter（相同 Base revision；历史权重身份必须先验 SHA/加载可用性） | **必须** | R47 旧 20 Prompt 中 11/20 多数偏好；R48 仅略逊原始 Gold；历史强质量对照 |
| C | R54 **v0.3-A checkpoint-16** Adapter（相同 Base revision；旧 frozen checkpoint） | **推荐同轮纳入，预注册为诊断臂** | R55 对 v0.2 旧题 12/20 多数偏好，但六维均分 3.2750 < 3.3972、自主权严重标记 9 > 7；历史 NO-GO 是不批准消耗 R50 密封测试，不是禁止在**新 P2 来源**上诊断 |
| D | **R60 Base336 checkpoint-37** Adapter | **必须；新实验主角** | 已完成工程训练与 Adapter reload，尚无独立质量证明 |

不将 **v0.1 checkpoint-9** 纳入核心新评估：旧 R47/R48 表现偏弱，对判断新模型是否超越历史最佳的边际贡献小，增加一次整套推理/盲审成本。**R48 原始 Gold 仅属于旧 20 Prompt，不能直接移植给 P2 新 48 题；但 Owner 已明确要求未来同题原始回答 Gold 作为匿名对照，必须按本文件第八节解决匹配与来源权限。**旧 R47/R48/R55 20 Prompt 仅涉及 2 个已暴露 Story，不能当新测试数据或替代本次预测。

- 推荐同一次锁定 **48 个新 Prompt × 4 个模型 = 192 份生成结果**。若资源限制且需要严格最短路径，明确降级为**3 个核心臂：Base、v0.2、Base336 = 144 份**；不应降到只有 Base/Base336 两臂。任何降级/是否纳入 v0.3-A **必须在首次查看 P2 生成及评分结果之前由 Owner 冻结**，不得看结果后再选择增加/移除臂。
- **主预注册比较**：Base336 vs Base、Base336 vs v0.2；**诊断比较**：Base336 vs v0.3-A；各臂均同一批 48 Prompt、逐案生成一次，同一 Model revision / Tokenizer / Chat Template / 三消息上下文 / 解码 / seed / stop / token budget。对每对模型的逐案结果、六维得分、严重自主权/禁句/安全标记独立报告，避免只用“四选一冠军”隐藏硬规则回退。
- 盲化时每条 Prompt 的四份回答随机匿名化，保留只在 Owner 的 create-only 0600 身份密钥；评审者不获模型名单对应关系。三名独立 Reviewer 的**独立性**需要实证，不能只凭不同 AI 模型 ID。48 prompts 分 8 世界、5 作者，按世界/作者聚类报告不确定性，不把 192 个输出或 Reviewer × Prompt 评分当作独立 Story。
- 旧 v0.1 / v0.2 / v0.3 数据与训练输入的 System/World/Rules 差异、部署 Prompt 分布差异必须披露；相同推理 Prompt 保证**操作层面可比**，不意味着唯一因果变量是训练数据。任何臂无法验证固定 Base revision、旧 Adapter SHA/加载、历史训练数据泄漏风险或完整 P2-C 许可时，**先 HOLD / 调整正式预注册**，不可静默替换模型。
- 本次变动只更新**方案**；P2-C=HOLD、48 真实 Prompt=NOT_GENERATED、P3 两/四臂 Backend 尚未实现、P4 GPU/HF 未授权、train/quality admission=0、model_promoted=false 均不变。复用 `generation_eval.worker` / HF Runtime，不为四臂重写底层执行器。

**历史决策依据：**
`docs/evidence/V02_R47_2_THREE_MODEL_UNBLIND_RESULTS_20261014.md`；
`docs/evidence/V02_R48_FOUR_ARM_UNBLIND_ANALYSIS_20261014.md`；
`docs/evidence/V03_R55_CHECKPOINT16_CANDIDATE_GO_NO_GO_20261023.md`；
`docs/evidence/V03_R50_OWNER_STORY_INDEPENDENCE_ATTESTATION_AND_R56_NEXT_GATE_20261023.md`。

---


> **最高优先级 / 直接复制给新 Agent。** 本文取代 2026-11-17 的通用启动提示词和 2026-11-18 的 P2 Crosswalk 提示词中的“当前步骤”与过期状态；旧文件保留为历史过程。若与旧文档的待办、授权要求或文件存在性判断冲突，先核对本文件引用的最新真实 SAFE，再以本文件的工作顺序为准。
>
> 仓库：`sunxu/storyforge`。当前执行 PR：[PR #31](https://github.com/sunxu/storyforge/pull/31)，工作分支 `docs/r60-p2-r47-r48-r55-source-shape-audit-20261118`，目标合并基线 `r60/common2-cpu2-owner`；这些是**截至 2026-11-19 的快照**，新 Agent 必须实时确认 HEAD / PR / CI，不假设本文件记载的提交永远最新。

## 一、唯一业务目标（禁止偏航）

完成已训练的 **R60 Base336 checkpoint-37 Adapter** 与对应 **Qwen Base** 的**新来源、真正独立、六维盲化质量比较**，进而给出有证据边界的质量结论，而不是继续审计旧 R50/R58、反复补写工具或证明模型已晋升。

固定路线：

1. **P0 / P1 已完成**：Base336 探索性 GPU 训练与工程产物核验；293 Train / 43 Validation；37/37 steps，Adapter reload，33/33 远端对象 inventory。模型**未晋升**。293/43 均不可做独立 Held-out，43 曾参与 Eval / checkpoint 选择。
2. **P2-A 已完成**：Owner 已批准 Supabase **8 条公开已发布原创 Story**（来自 5 位作者、8 个不同 World JSON），逐条 revision、moderation snapshot、permission 绑定完成；授权仅限**内部独立评估提示构造**，并非训练、公开发布、再分发授权。不得查询私有会话正文。
3. **P2-C 当前主要阻塞**：对这 **8 条新 P2 来源**证明与已训练/验证、受保护/保留、历史开发/训练/教师暴露来源之间的精确身份和**实质世界/角色/剧情/开场语义**隔离，证明真实历史版本/actual-sent 与受审范围、进行可核验的独立 Reviewer 审查及 Owner 冻结。**不得将只证明局部精确 ID 零交集的 SAFE 升级为 P2-C PASS。**
4. **P2-B（在 P2-C 及用途权利门禁完成后）**：构造并冻结 **8 × 6 = 48** 条真实提示 JSONL / Manifest / SHA256，Quality-v1 六维各来源各 1 条：`chinese_prose`、`character_consistency`、`npc_initiative`、`player_agency`、`rule_fidelity`、`narrative_continuity`。每条是新编 `user / assistant / user` 三条可见持久化消息，**无 System、模型生成输入无参考答案、无私有历史对话**；逐条核验公开素材忠实性、权限、无未来信息、无原文长段复制、无隐藏指令/冒称源事实。当前**没有真实 48 条包**；既有 9/9 是合成测试。
5. **P3（P2-C 后）**：只制作本任务必须的 Base/Adapter 两臂薄适配器与合成测试，优先复用 `generation_eval.worker.run_generation_batch`、`hf_runtime.inputs/outputs`、`GenerationBackend`、现有配对/盲化思路与 `experiments/r58_quality/quality_v1.py`。不写另一套生成循环/IO/六维 Rubric，不修改旧 P4 三臂冻结 Profile。
6. **P4 / P5（另行授权）**：同一冻结 Base revision、checkpoint-37 Adapter、同 prompt SHA、Tokenizer/Template、三消息上下文、seed/解码/Token 上限/stop 条件配对生成；私有 A/B 密钥隔离，独立 Reviewer 六维盲审，重视严重 `serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion`，Owner 裁决。**任何新 GPU/HF 推理、训练或付费任务必须就具体运行另行明确授权**；本任务目前没有此授权。

## 二、最新真实证据状态（2026-11-19）

| 子任务 | 已关闭的实际结果 | **尚未关闭、不能外推** |
|---|---|---|
| P2-A 8 个公开来源 | 8 sources / 5 authors；snapshot、permission、revision 与 World metadata 绑定 READY | P2-C 语义、历史曝光与 Owner 最终冻结 |
| P2 × Base336 冻结身份 | 336 cases / 172 distinct Story，**8 × 172 精确 Story ID overlap=0**，离线捕获范围预检 PASS | 全 172 Story 当前+存档 `world/character/characters/opening` 来源包**尚未生成**；Owner 捕获 `DB_BASE336_SOURCE_QUERY_HOLD`，未有根因证据或全覆盖语义 PASS |
| 旧 Base336 八组成员分析 | 历史 8 组 World，38 Story / 59 当前+存档来源记录已核验；旧 10 条跨拆分候选边图含 16 Story / 35 cases；A/B 表单已填写，B 资格尚未由 Owner 验证 | 这些是**旧 Base336 内部冲突**，**不是新 P2 8 来源**的隔离证明；旧 Reviewer A 无合格独立性证据，B 待 Owner 核验 |
| R50 原始 50 → 46 + 4 | 原始 provenance 50、派生 46、排除 4 元数据补集严格 PASS；密封题目未打开 | R50 正式 sealed cases 字节/Final Seal 不是本轮复核；**其他 Protected/Reserved 世界权威全集**仍 HOLD |
| R50 冻结五世界 | 固定 Git 两份 SAFE Blob 锁定 W16–W20、5 个 Story / 5 个 Session / 35 源文件；Owner 核对五个固定 Story UUID **恰等于原 50 provenance 所有来源 Story 集合**；P2 × 五世界精确交集 **0** | 五世界之外的 Protected/Reserved 源、隐藏语义别名及覆盖权威性均未证明 |
| R47/R48/R55 旧开发链 | 同一 **20 Prompt = 2 个 Story**；R47 Sample→canonical Test Story ID、R48 source SHA、R55 三层 Index **76/68/46** / 20/20 回链已 PASS；P2 × 该链精确交集 **0** | **其他**历史 Dev/仲裁、Teacher、训练、独立保留来源完整暴露全集仍 HOLD |
| R58 旧五范围 CSV | Owner 实际回执：5 行全部 `MISSING_SOURCE_REFERENCE`，`source_files_present_unopened=0` | 只表示这个旧 CSV **没有绑定来源引用**，不代表源文件不存在；**不要再使用/重跑**来冒充 R60 全集证据 |
| 版本/审查 | P2 元数据快照已绑定；旧 38 Story 有静态版本证据 | Base336 历史 `actual-sent`、全部语义世界组件源引用、P2 8 新来源 Reviewer 独立执行与 Owner Freeze 仍 HOLD |

原始已通过 SAFE 的关键路径（GitHub 可公开、没有私人 ID / 原文）：
- `docs/evidence/R60_P2_R50_50_46_4_PROVENANCE_COMPLEMENT_SAFE_20261119.json`
- `docs/evidence/R60_P2_R50_PINNED5_TO_PROVENANCE_OWNER_SAFE_20261119.json`
- `docs/evidence/R60_BASE336_P2C_MAINLINE_GATE_STATUS_SAFE_20261119.json`（衍生状态投影，不是独立 Owner 执行）
- `docs/evidence/R60_P2C_R58_G1_EMPTY_SOURCE_REFERENCES_OWNER_SAFE_20261119.json`
- `docs/evidence/R60_P2_R47_R48_R55_SOURCE_SHAPE_AUDIT_20261118_CN.md`
- `docs/plans/R60_BASE336_P2_PROTECTED_CROSSWALK_EVIDENCE_INDEX_20261118_CN.md`（历史与最新附记并存，避免误读旧段）

## 三、**禁止重复清单**（除非发生可验证的输入版本变更）

不再执行：P2-A 8 来源再次筛选/数据库重抽；R50 50/46/4 补集；R50 已固定 5 世界与原 50 来源身份比对；R47/R48 20-case / R55 三层 SHA 与 Token 链；R58 五行空白 CSV；Base336 旧 38 Story/59 records 的 Card/Opening 提取、结构审核；旧 10 边/35 案例冲突预览；293/43 训练/33 产物审计；相同 Base336 全量 SQL 的猜测性重试；生成、重造或覆盖既有私有包。

旧 Reviewer B 的独立资格**仍不等于已认证**，但此事不是当前推进新 P2 8 来源的第一阻塞；不要让旧 35 案例审查反客为主。所有旧结果仅继承其**已证实范围**。禁止为补出漂亮的 PASS 擅自修改冻结数据、换 Story、猜来源、填虚构空白索引、放宽 DB RLS 或将历史匿名评测重新包装成新 Held-out。

## 四、下一 Agent 第一轮应做的**真正新增工作**

1. **定位最后一个能推动 P2-C 的证据缺口**，不要先跑工具：核对 GitHub PR #31 当前 HEAD / Actions 与上面列出的最近 SAFE；给出简洁的“已覆盖集合 → 对 P2 8 来源还缺什么 → 现存可信来源路径 → 可获得性”对照表。已有证据不再计为新成果。
2. **优先针对新 8 P2 来源**形成真实、可审核的语义隔离裁决准备：复用 Owner 本地的已批准 P2 Source Manifest、Base336 冻结 roster、现有成员级 World/Character/Opening 证据与 `src/storyforge_dataset/world_isolation.py`。严格区分精确 ID 零重叠、字段相等、专属角色/组织/地点/事件复用、独立模板，以及完整语义组件同源；每项冲突要有 Owner-only 来源字段、版本与证据引用。**不对旧 Base336 十条边再启动 Reviewer**。已存 38 Story 是部分样本，未核验其余 134 Story 及归档版本的不能静默 PASS。
3. **处理全 172 Story 的数据可获得性，不重复盲调**：既有捕获脚本 `experiments/r58_quality/r60_base336_p2_source_evidence_capture_cpu.py` 在 Owner Mac 停于 `DB_BASE336_SOURCE_QUERY_HOLD`。先查是否存在同版本、可信赖且来源完整的 Owner 本地冻结快照/原版证据可直接复用；若没有，**只在能指认 SQL 执行失败的真实原因与最小修复时**使用已授权的只读 DB 权限推进一次有界恢复，勿不断新增捕获器或扩大权限。证据缺失如实 HOLD，绝不按当前 DB World 值冒充历史实际发送。
4. **旧保护/暴露全集只做未关闭的差集**：R50 的 W16–W20 五世界已闭合；R47/R48/R55 同一 20 Prompt 已闭合。剩余明确是旧 R58 权威来源缺口标签 `r55_r57_other_dev`、`other_reserved_heldout`、`other_historical_training`，以及本 R60 阶段其他真实暴露索引。寻找**经授权、冻结且有来源版本/截止边界**的 metadata-only roster；按世界组件和来源绑定审核，不重做 ID 计数。没有权威全集时写明 UNKNOWN/HOLD 与缺少的确切 source authority，不要无期限扫描全机器或重复运行空索引。**R50 只读身份/保护 metadata，绝不打开密封正文。**
5. **独立 Review / actual-sent / Owner 冻结**：明确新 8 来源当前的独立审核能否执行、历史真实发送内容/版本的证据是否存在。Review 必须独立并有版本化证据引用，不能把已知旧 Reviewer 的主观意见或签字当作 P2 新来源 PASS。Owner 冻结前只保留候选，不宣称正式 P2-C 通过。
6. **收敛而非扩散**：完成一项真实闭合的证据后更新统一 SAFE/文档；若根本缺少权威来源证据，提交清晰的“现有证据不能证明什么 + 最小可信新证据”结论，并推进其它不依赖的既定主线事项。不以单纯加文档、补 CI、旧文件存在性检查或合成测试自称 P2-C 进度。

## 五、权限、代码复用和验收规范

- Owner 已于本轮明确授权 **StoryForge 本任务必需、限定只读范围**的数据库核验，**后续这类只读访问无需逐次重复请示**；继续执行 read-only/RLS、最小字段与固定 ID 过滤。**不授权**写库、读 R50 密封题目/答案/私有聊天、扩大版权用途、修改冻结 Train/Validation、模型推理、GPU/HF 或训练。
- 既有核心优先：`world_isolation.py::validate_component_review_assignments`、`component_split_conflicts`；Owner R50 provenance / protected IDs 复用 `r60_r50_original50_complement_cpu.py` 与 `check_r50_protected_uuid.py`；来源包结构预检 `r60_p2c_existing_source_package_preflight_cpu.py`；P2 Prompt gate `r60_base336_p2_public_prompt_package_gate.py`；P3 则复用 `generation_eval.worker`、HF Runtime。
- 必须区分 **P2 新 8 来源** 与 **Base336 旧 8 组 World**；区分 **20 Prompt** 与 **2 个 Story**；区分“文件存在”、“来源元数据闭合”、“完整语义隔离”、“真实历史发送”和“Owner 冻结”，任何一个都不能代替另一个。
- Owner 私有文件、完整 Story ID/UUID、版本映射、逐条证据引文、SHA Manifest、Reviewer 身份与密钥全部留在 Owner 0700/0600 路径。GitHub/聊天仅放 SAFE 聚合、合成测试与必要的公开代码；不得输出私有正文、连接串、异常原文或逐案映射。
- 每次需要提交代码前先确认现有函数不能完成任务；只作最小必要修复，不为追求“诊断完备”反复扩展工具。GitHub 使用 PR #31 当前分支；不 force push、不覆盖其他 Agent 私有成果；每次提交检查**该 HEAD** 的 CI，不把合成 CI 当作真实来源验收。
- **硬状态不变**：`P2_A=READY`、`P2_C=HOLD`、`P2_B_48_PROMPTS=NOT_GENERATED`、`train_admitted=0`、`quality_v1_admitted=0`、`model_promoted=false`。无新权限不得提交 HF Job 或启动 GPU；在 P2 仍 HOLD 时不得产出正式 48 prompt 包或投入配对推理。

## 六、完整任务书与交接时的输出格式

先读：
1. `AGENTS.md`；
2. `docs/plans/R60_BASE336_POST_TRAIN_QUALITY_EVALUATION_20261117_CN.md` 与 `docs/plans/R60_BASE336_SUPABASE_PUBLIC_STORY_P2_ADDENDUM_20261117_CN.md`（总体目标、用途权利与六维合同）；
3. `docs/R60_BASE336_P2C_MAINLINE_NEXT_ACTION_20261119_CN.md` **最顶部最新 Owner 结果**与 `docs/evidence/R60_BASE336_P2C_MAINLINE_GATE_STATUS_SAFE_20261119.json`；
4. 上述已通过 SAFE 原件与 `docs/plans/R60_BASE336_P2_PROTECTED_CROSSWALK_EVIDENCE_INDEX_20261118_CN.md` 的最新段落；
5. 仅在实际动手前读直接相关代码及合成测试，**不必逐个复演历史脚本**。

新 Agent 首次答复应有：当前 HEAD / PR CI；一句话重申最终 **48 prompt → 两臂生成 → 六维独立盲评** 目标；按来源范围拆分的 **PASS / HOLD 与最新 SAFE 引用**；**已证明的内容不再重复做**；下一项最短能实际闭合的 P2 新 8 来源证据动作；无需新代码时明确“不改代码”；是否访问 DB、提交 HF / GPU、读保护内容；新结果若无法产生，也必须准确说明缺少哪一种权威证据。**不要以新的空泛审计任务书代替推进工作。**
