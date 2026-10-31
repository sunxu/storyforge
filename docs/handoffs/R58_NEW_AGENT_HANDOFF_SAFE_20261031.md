# StoryForge R58 — 新 Agent 全量交接（SAFE）

**交接基准：2026-10-31；基准 HEAD：`c7f0b1d4b230b9868c406c7b28d4412c78feb434`（交接文档提交之前）。** 项目在 `sunxu/storyforge`，分支 `r58/roleplay-sft-skill-v01`，Draft PR [#7](https://github.com/sunxu/storyforge/pull/7)。这份 SAFE 文档可直接供新会话使用，但**不是**访问私有材料、训练或放行的授权。新 Agent 需重新读取 GitHub PR HEAD，不要将本文的旧 HEAD 当成持续不变的分支指针。

## 1. 先看结论：代码验收和历史准入是两回事

| 项目 | 2026-10-31 终态 | 证据等级 |
|---|---|---|
| Skill v0.2 合成测试 | **Owner Mac 80/80 PASS**，0 failures/0 errors，0.014 s | Owner 终端回报，未宣称 GitHub Actions 或独立重跑 |
| Skill v0.2 Ruff | **RUFF_V02_PASS，0 错误** | Owner 终端回报，UP017/RUF007 已修复 |
| 已冻结 Skill v0.1 | 原始结构工具不改、不自动调用其 `freeze` | Git 分支隔离及 v0.2 桥接契约 |
| G1 历史曝光及保护来源 | **HOLD** | 部分来源的 SAFE 交集验证，不是历史全集 |
| G2 历史 Provider 输入还原 | **HOLD** | 请求身份、运行时历史和 17 项字节级阻塞尚未解 |
| G3 独立 Reviewer / Owner 正式准入 | **NOT_STARTED** | 未获 G1/G2 放行 |
| Train / Validation / Teacher 准入 | **0 / 0 / 0** | 固定门禁 |
| Round1 扩样 | **false** | 首轮未完成，未经 Owner 明确再授权 |
| PR #7 | **Draft，未合并** | GitHub 实时检查基准 |

最新实测回执：`docs/evidence/R58_OWNER_V02_80_PASS_RUFF_ZERO_POSTFIX_SAFE_20261031.json`，归档提交 `c7f0b1d4b230b9868c406c7b28d4412c78feb434`。此前 47/61/80 测试、Ruff 2 错误等中间状态仍有历史文档保留，**按上述最新 Owner 实测判定代码验收**。测试 PASS **不得**推断真实 G1/G2 PASS。

## 2. 固定选样范围与硬约束

- Round1 最多 5 个世界 / 20 条回复，原始固定五候选**不可补选**。经既有历史 SFT 精确 UUID 对账，**1 世界已排除，剩余 4 世界 HOLD**。
- Owner 已在本项目定义 `ONE_ROLEPLAY_STORY_UUID_PER_WORLD`，即同一 RolePlay story UUID 视为同一世界。无需重新提出跨 UUID 别名世界图；**仍必须证明历史来源全集及保护集独立性**。
- 旧 `R50` 冻结五世界、Gold195 的 13 个来源世界、legacy DEV20 的 2 世界、R04 非 Gold 的 2 世界有局部 UUID SAFE 结果；R55/R56/R57 其他 DEV、reserved/heldout、其他训练来源没有权威完整索引。
- R50 只能接触**已获授权的 UUID-only 保护世界元数据**。不得读取/泄漏 R50 密封题目、答案、评分、候选历史、原始 Prompt 及故事正文。
- 不修改 `main`、不合并/关闭 Draft PR、不改 v0.1 冻结文件、不修改现存 PRIVATE 回执、不自动提交训练、不启动任何收费 HF CPU/GPU Job、不扩样、不冻结 Dataset v0.4、不擅自提级模型。
- 私有材料只留在 Owner 本地 `~/.storyforge-r58-private/` 的 0700 私有目录/0600 文件中；禁止上传 GitHub/聊天/CI 输出。所有私有读取都需事先明确授权范围；不为填补源缺口编造日期、UUID、SHA256、回执或运行结果。

## 3. G1 — 已核与仍待证

**已核局部范围**：五个已知参数更新 HF Job（v0.1 三个，R46 一个，R54 一个）关联的**当前** 12 个 HF 输入对象与既有来源 pin 对账；六份历史 Train/Validation 冻结 split 共 **184 个记录位置**（145 Train、39 Val），五个 Job 的重复输入合计 **344 个 Job 关联记录位置**。**这些都不是去重样本数，也不证明当时 Job 真实读取的字节/发生梯度更新。** Owner 私有元数据报告 27 个旧 SFT 世界。

**历史 Job 未分类**：曾对 `adradar` 返回 69 个可见 Job：五个已知更新、四个有非训练用途文档、剩余 **60 个未充分分类（18 GPU / 42 CPU）**。CPU、取消、失败或未检测到日志迹象 **均不能自动排除**。18 个 GPU 日志已做过 1 个潜在线索 / 17 个未见训练信号的先期扫描，**不要重新批量扫描**。

**优先单个 CANCELED GPU Job**：已有 Owner 私有优先账本和 Provider 元数据回执，经 `r58_existing_priority_receipt.py` 交叉核验 PASS；`provider_started_at_present=true`、`provider_finished_at_present=false`、`command_intent_class=NOT_ACCESSED_NO_OWNER_OPT_IN`。日志曾出现 `TRAINING_LOSS_GRAD_TELEMETRY`，但**真实 optimizer step 既未证明发生，也未证明没有发生**，输入 SHA256 也未验证。禁止因 CANCELED 或两份回执内部一致而判定排除。

**下一份真正有用的材料**：与该历史 Job **直接绑定**的已有原始 Trainer 运行摘要（优化器/global_step、Checkpoint、实际 Train/Validation 输入哈希、Job/worker 来源和版本）。先核实已有工件索引及授权，再做范围极小的只读验证；若无原始凭据就维持 PENDING/HOLD。并行补齐 R55/R57 等 Protected/DEV 元数据来源完整性；不能以 Owner 自报 `OWNER_COMPLETE` 替代权威证明。

入口文件：
- `docs/evidence/R58_G1_G2_SKILL_V02_READINESS_MATRIX_SAFE_20261031.json`
- `docs/evidence/R58_G1_KNOWN_FIVE_JOB_CURRENT_PRIMARY_INPUTS_CROSSCHECK_SAFE_20261031.json`
- `docs/evidence/R58_OWNER_V02_61_PASS_EXISTING_PRIORITY_CROSSLINK_SAFE_20261031.json`
- `docs/evidence/R58_G1_SCOPED_UUID_CONTRACT_RUNBOOK_SAFE_20261031.md`
- `skills/storyforge-roleplay-sft/v02/r58_g1_scope_reconcile.py`
- `skills/storyforge-roleplay-sft/v02/r58_existing_priority_receipt.py`
- `experiments/r58_round1/check_hf_training_job_inventory.py`

## 4. G2 — 字节级 Prompt 还原不能偷换成时间猜测

**固定三条 Priority3 目标**：当前历史消息/修订可做局部结构对账：三组每组条件性 11 消息、合计 33 消息。Prompt 组装识别 19 项组件、**17 项字节级阻塞**。日志层 `v2_chat_request_events.request_id` ↔ `chat_latency_metrics.request_id` 曾有 9/9 关联，但**不等于** target Assistant UUID ↔ request ID 直接关联。软时间线仍为 **2 / 4 / 2** 多解；不得用最近时间、相同会话、`v2EventClaimId`、现存 `v2_data` 或当前 Session 摘要捏造请求身份。

源码 pin：`sunxu/RolePlay@e9fe29c42434caeb0bac5acc91845ab4741ecb2b`。对 7 个冻结源码文件、13 个调用点的只读审计确认：API requestId 用于 Provider 调用选项、终态事件和诊断指标；**在已检查的 Assistant 流式/非流式持久化路径中未发现显式将 API requestId 写入消息元数据**。这**不是**所有历史部署或其他写入者的全局阴性证明。某些异常快照路径可能同时持有 requestId 与 turnIndex，但敏感、异常专用、可能过期，**未读取**。

部署证据：冻结 RolePlay 部署脚本写 `DEPLOYED_SHA`，但该文件可覆盖，**不是**历史连续版本账本；固定脚本中的 `workflow_run_id=manual-local-build` 是字面量，**不是** GitHub Actions Run ID；旧 staging 默认最多保留最近 3 份或在超过 7 天后可能清理。公开 build ID 8 位前缀、GitHub CI 记录或当前部署 SHA 不足以验证目标时点实际 Serving Backend。现有 GitHub 查询未取得可信历史部署成功区间。

最新离线 `r58_deployment_interval_audit.py` 只结构核对**Owner 已存在的**三目标时间与最多 96 个部署区间，拒绝错误时间、重叠区间和无效 SHA，始终输出 G2=HOLD；**没有既存真实回执时不要新建假 manifest，也不要求执行该核验器**。即使 3/3 覆盖也未证明历史发布真实性或 Provider 原始字节。

G2 来源：
- `docs/evidence/R58_G2_PINNED_REQUEST_ID_PERSISTENCE_SOURCE_AUDIT_SAFE_20261031.json`
- `docs/evidence/R58_G2_DEPLOYMENT_SHA_SOURCE_PROVENANCE_SAFE_20261031.json`
- `docs/evidence/R58_G2_DEPLOYMENT_PROVENANCE_RECOVERY_RUNBOOK_SAFE_20261031.md`
- `docs/evidence/R58_G2_EXISTING_DEPLOY_INTERVAL_OFFLINE_AUDIT_RUNBOOK_SAFE_20261031.md`
- `docs/evidence/R58_PRIORITY3_REQUEST_LINK_STOP_RULE_AND_NEXT_GATES_SAFE_20261030.md`
- `docs/evidence/R58_PRIORITY3_PROMPT_ASSEMBLY_GAP_MATRIX_SAFE_20261030.json`

**真正解关还需**：目标→实际 request 的可信因果绑定、实际目标时点部署 SHA/Backend、当时 Session/summary/memory/flags、Provider 调用消息与参数及准确的历史字节/可靠等价证明。没有这些证据就停止启发式重构，不进入 G3。

## 5. Skill v0.2 代码路径及可重复执行

重点文件：
- `skills/storyforge-roleplay-sft/v02/README.md`
- `r58_evidence_preflight.py`：只读固定 SAFE Git blob，合并 G1/G2 状态；HOLD 不可变成 PASS。
- `r58_pipeline_bridge.py`：`shortlist` 只发现元数据；`gate/freeze` **强制拒绝**、不调用 Skill v0.1；`g1-audit` 对已有私有 UUID 清单做限定范围核对。
- `r58_g1_scope_reconcile.py`：`O_NOFOLLOW`、dirfd、权限/大小/硬链接保护；本机 POSIX `OSError` 已标准化为 `Hold`。
- `r58_existing_priority_receipt.py`：已有 PRIVATE CANCELED Job 元数据内部交叉核验；不调用 HF。
- `r58_deployment_interval_audit.py`：Owner 历史部署区间**结构**预检，任何通过均不触发 G2 PASS。

Owner Mac 已执行最新源码 80 项测试和 Ruff 零错误（UP017→`datetime.UTC`、RUF007→`itertools.pairwise`，修复提交 `24c52f48b075bece1b2635b601173e2edde84c55`）。**本次交接新增 Markdown/JSON 不改变测试代码，旧 README 内较早的“待 44/47/61 测试”描述只是历史里程碑。**

```bash
cd ~/workspace/storyforge-r58-run
git fetch origin
git switch r58/roleplay-sft-skill-v01
git pull --ff-only
git rev-parse HEAD
python3 -m unittest discover -s skills/storyforge-roleplay-sft/v02 -p 'test_*.py' -q
ruff check skills/storyforge-roleplay-sft/v02/ --statistics && echo RUFF_V02_PASS
python3 skills/storyforge-roleplay-sft/v02/r58_evidence_preflight.py --repo-root "$PWD"
python3 skills/storyforge-roleplay-sft/v02/r58_pipeline_bridge.py gate --repo-root "$PWD"
# gate 的 42 退出码为预期拒绝，不能写成 PASS
```

不要重复跑 Owner 已成功的测试作为“证据进度”；上述仅供新环境验证代码。若 `git status --short` 显示 Owner 本地未提交更改，先核对并保护，不做强制 reset/清理。

## 6. 新 Agent 推荐步骤（严格取证优先）

1. **只读核对** PR #7 的 HEAD、Draft 状态、最新 80 PASS 回执、八范围 G1/G2 矩阵及首轮完成文件是否真实存在。不要让时间已过的准备手册覆盖最新结论。
2. **G1：寻找真正增量证据**，先从已知 SAFE 索引检查单个 CANCELED GPU Job 是否已有独立原始 Trainer 工件登记；优先在 Owner 有权访问的既存工件上做限定字段的本地核验，私有日志/Job 参数仍需单独授权。若无，明确停止并保持 PENDING。
3. **G1 并行：保护集完整性**，为 R55/R56/R57 和 other reserved/heldout 的 Owner-private UUID-only 来源确定权威性/版本及无覆盖缺口；必须将已核局部集合与全集证明分开。
4. **G2：历史部署来源**，仅查已保存的部署/回滚元数据真实性、目标时点活跃版本和 Backend；没有来源不编造区间、不自动 SSH/查生产日志。其后才探查独立消息↔请求的直接记录和 Provider 字节。
5. **只有新的真实证据**才修改门禁；若缺口仍在，提交可验证的 SAFE 结论及停止条件即可，不为制造进度而无限增加同构合成工具或重复审计日志。
6. G1/G2 真正独立批准后仍限原有最多 5 世界/20 回复，走 G3 双 Reviewer 与 Owner 逐项审核；**首轮完成与扩样是两个独立审批动作**。

## 7. Round1 完成文件 / 自动提醒状态

截至交接前基准 HEAD，精确路径 `docs/evidence/R58_ROUND1_PILOT_COMPLETION_SAFE.json` **不存在**。不能自行伪造顶层 `status=R58_ROUND1_PILOT_REVIEW_COMPLETE`；仅首轮实际审查完成、独立验收后才有资格写入此文件。已有每日只读提醒只在真实文件存在且状态严格匹配时提示 Owner **是否批准扩样**，不代表扩样自动获批。

## 8. 引用与交接原则

权威状态顺序：**最新 PR HEAD + SAFE 原始回执 + Owner 最新本机实测 > 旧 README/阶段准备文档 > 仅代码推测**。独立核验的历史事实必须另有权威一手工件；文档中的布尔/哈希自报只是局部证据。GitHub 只允许提交 SAFE 聚合/文档/经审查工具，私有 UUID、R50 试题、Trainer 样本、真实 Provider 请求、HF tokens、SSH 参数和服务器隐私信息不得上推。

如新 Agent 无法访问连接器或 Owner 私有目录，应如实标注不可验证，**不要要求把 PRIVATE 文件粘到聊天来绕过门禁**。新 Agent 可用同目录的 `R58_NEW_AGENT_START_PROMPT_SAFE_20261031.md` 直接开始。
