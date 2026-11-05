# StoryForge R58 — 新 Agent 接手后增量核验与后续工作规划（SAFE）

- 归档日期：2026-10-31
- 对象：`sunxu/storyforge`，工作分支 `r58/roleplay-sft-skill-v01`，Draft PR #7
- 本次读取时的基准 HEAD：`62d7dcd847a7dd485c40a63fbba0d1855bc3135f`
- 证据类型：GitHub 只读源码／仓库文件元数据的增量复核 + 既有 SAFE 回执的有界引用；**不是** HF、Owner PRIVATE 文件、生产服务器或 Provider 的原始运行工件认证
- 本次目的：保存交接后已完成的独立 GitHub 核验、证据断点和下一位 Agent 的唯一优先取证路径；不重复合成测试、不制造虚假准入进度

## 1. 状态与硬边界

| 项目 | 当前状态 |
|---|---|
| PR #7 | OPEN、DRAFT、未合并，base=`main` |
| Skill v0.2 | Owner Mac 80/80 PASS、Ruff PASS，**OWNER_REPORTED**；该回执未同条打印精确 `git rev-parse HEAD` |
| Skill v0.1 | 冻结，不更改 |
| G1 | **HOLD**：历史 Trainer 参数更新／实际输入全集及 Protected/DEV/heldout UUID 全集均未认证 |
| G2 | **HOLD**：target↔request 身份、历史 Serving Backend/部署 SHA、Provider 原始请求字节均未认证 |
| G3 | NOT_STARTED |
| Train / Validation / Teacher | **0 / 0 / 0** |
| expansion_allowed | **false** |
| Round1 | 固定原始五世界、最多 20 条回复；历史 SFT UUID 精确重叠 1 个已排除，剩余 4 个 HOLD，不补选 |
| 首轮完成回执 | `docs/evidence/R58_ROUND1_PILOT_COMPLETION_SAFE.json` 在本次基准 HEAD 的 GitHub 文件查询中为 404；**不得伪造** |

旧交接状态文件记载的基准 `c7f0b1d4b230b9868c406c7b28d4412c78feb434` 到本次基准 `62d7dcd847a7dd485c40a63fbba0d1855bc3135f`：GitHub Compare 为 ahead 3、behind 0；差异仅为三份新增交接文件，不能据此宣称代码本机重新运行过。PR 本轮新增的这份文件亦不是 Skill 行为或准入条件变更。

## 2. 本轮真实新增核验：G1 原始 Trainer 证据定位

1. GitHub PR #7 当时共有 191 个变更文件；**仅在这个 PR 的变更文件清单范围内**，未找到命名为 `trainer_state.json`、`optimizer.pt`、`checkpoint-*/...` 等原始 Trainer 工件的归档路径。**不代表**整个仓库、HF Bucket、Owner 本机或历史服务器不存在这些文件。
2. 从当前 HEAD 直接读取 `docs/HF_RUN_REGISTRY.md`（Git blob `5a5c1ed11bf30bd763480b7c17ac366579e64dc0`）发现已知 **v0.1 baseline** `checkpoint-9` 文件清单中列有 `trainer_state.json`、`optimizer.pt` 的历史 SHA256 和大小记录。这是**另一个已知完成的 baseline Job**，不可移植为待调查的 CANCELED GPU Job 的 Trainer 工件证据。
3. 已有 `R58_OWNER_V02_61_PASS_EXISTING_PRIORITY_CROSSLINK_SAFE_20261031.json` 仅报告两个**既存 PRIVATE 元数据回执内部**的 Job/日志摘要一致，且 `provider_stage=CANCELED`、有 `started_at`、无 `finished_at`、`command_intent_class=NOT_ACCESSED_NO_OWNER_OPT_IN`。不能推出参数更新已发生或从未发生，也不证明真实输入字节。
4. 已知 5 个参数更新 Job 的当前 12 个 HF 输入对象一致性，属于 Owner 回执与 GitHub 冻结索引交叉核对；此前 69 个可见 Job 中的 60 个未充分分类（18 GPU、42 CPU），也不能自动视为无曝光；历史 Job 全集未证实。六份已知 Train/Validation split 共 184 个**位置**，五 Job 对应 344 个**位置**，两者均非去重训练实例数。
5. R50 五个冻结世界与剩余四候选的局部 UUID 精确交集为零是 Owner 已报告的范围内结果；R55/R56/R57、其他 Protected/DEV/heldout 与可能缺失历史平台/Job 的权威全集仍未完成。既定世界身份规则为 `ONE_ROLEPLAY_STORY_UUID_PER_WORLD`，但身份规则不是来源全集证明。

**G1 新增结论：** 当前公开可访问的 GitHub 证据能定位“已知 baseline 有 Trainer 工件登记”与“待调查 CANCELED Job 缺独立 Trainer 证据”的区别，尚不足以对 CANCELED Job 进行实际参数更新／无更新定论。禁止重跑先前日志扫描或将失败／取消／CPU Job 直接排除。维持 G1 HOLD。

## 3. 本轮真实新增核验：G2 原始 RolePlay 代码交叉检查

直接在 `sunxu/RolePlay@e9fe29c42434caeb0bac5acc91845ab4741ecb2b` 读取以下固定源码（该源码 **不是**目标时点实际 Serving Backend 的部署认证）：

| 固定文件 | Git blob SHA | 本轮具体观察 |
|---|---|---|
| `.github/workflows/deploy.yml` | `f1af1a7e1431c51bddf31b3acdc75f56447042e8` | `ROLEPLAY_BUILD_SHA=github.sha`；`.deployment-window` **在远程成功部署前**写入；`if: always()` 尝试收尾，因此单独存在 window 不代表成功切流 |
| `ops/deploy/deploy-standalone-release.sh` | `476323356f58b445ebc86cec08abdca2243ac2d4` | 成功路径写 `DEPLOYED_SHA`，但使用覆盖写入；`workflow_run_id=manual-local-build` 为**固定字符串**，非可信 GitHub Run ID；旧 staging 可能清理 |
| `src/app/api/chat/v2/route.ts` | `48f177570fa18454eab768f2800c82fa1da07e57` | 终态请求事件写 API `requestId`；已审流式 Assistant 占位／完成及非流式保存调用点未显式把相同 API request ID 写入 Assistant 持久化元数据 |

审计代码位置：`deploy.yml` 约 161–168、260–326；`deploy-standalone-release.sh` 约 536–555；`route.ts` 约 1027–1040、3745–3759、7148–7201。本轮 GitHub 针对上述固定 RolePlay commit 的 Actions 查询返回**零条 PR-triggered workflow runs**；该接口按 commit 且只含 PR-triggered 第一页，不能推断没有 push/workflow_dispatch/本地实际部署，更不能认定该 SHA 的历史生产 Serving 区间。

继承既有边界：冻结 3 条 Priority3，条件性每条 11 条历史消息、合计 33 条当前来源/修订对账；19 项 Prompt 组装组件中仍有 17 个字节级阻塞；日志层 request-event↔latency 的 9/9 request_id join **不是** target Assistant UUID↔API request_id；软时间候选 2/4/2 **不可用于唯一指认**。

**G2 新增结论：** 部署工作流中的 `.deployment-window` 同样不能单独充当历史成功切流证明，因为写入先于 Remote Deploy，失败也可能收尾；现有源码与 GitHub 工作流查询不能认证历史目标时点的 Serving Backend。必须有独立历史成功发布＋回滚边界及目标请求所经后端的可信记录，之后才可论证 request 身份和原始 Provider dispatch 字节。维持 G2 HOLD。

## 4. 下一阶段按优先级执行（只对新增一手证据行动）

### P1 — G1：单个 CANCELED GPU Job 的原始 Trainer 工件（**最高优先级**）

- 仅在 Owner 明确授权**该单个既有 Job、既存历史工件来源、允许字段、输出范围**后，私有环境只读核验是否有直接绑定的 `global_step` / 实际 optimizer 更新记录、`trainer_state.json`、Checkpoint 输出/写入证据、原始 Runner/版本，以及实际 Train/Validation 输入 SHA256。
- 必须分辨“作业声明打算训练”“有 loss/grad 遥测”“实际 optimizer 更新”“具体案例参与梯度”四种不同证据等级；若仅有 `CANCELED`、启动时间、近似日志或无来源文件，仍为 **PENDING/HOLD**。
- **停止条件：** 原始工件不存在、权限未获批准、无直接 Job 关联或无法确认历史输入字节，即停止此支线；不得因此新增 HF Job 或使用别的 baseline 工件代替。
- **允许的 SAFE 输出：** `source_class`、`job_link_authenticated`、`trainer_steps_evidenced`、`checkpoint_bound`、`train_input_bound`、`validation_input_bound`、`historical_immutability_proven`、`verdict=HOLD|EVIDENCE_FOUND_PENDING_G1_UNIVERSE`；不回传 PRIVATE Job ID、工件路径、原始日志/命令、训练内容或哈希。

### P2 — G1：完整训练曝光和保护世界 UUID-only 来源

- 收集既存、已授权的 R55/R56/R57、其他 DEV/heldout/reserved、既往所有 SFT Train/Validation/teacher 来源及历史 Job/平台/命名空间的权威**版本与覆盖声明**。
- 必须区分已核局部交集、各来源覆盖完整性、历史 Job/平台全集；不因对 R50 五个世界的精确零交集宣告 G1 PASS。
- **停止条件：** 任一受保护来源未覆盖、历史实际训练来源集合未证实完整、或语义/身份来源版本未认证，则 G1 继续 HOLD。
- 不读取 R50 密封题目／正文，不重新抽选剩余四候选；仅在已获许可的 Owner 私有环境读取必要 UUID-only 元数据。

### P3 — G2：真实部署与请求身份

- 首先寻找**已存在且可认证**的历史成功部署／回滚回执、完整 40 位 SHA、生产切流时间、目标时点实际 Serving Backend/路由和连续激活区间；当前 `DEPLOYED_SHA`、`.deployment-window`、公开 8 位 Build ID、源码 pin、单次 CI PASS 或 staging `deploy.status` 均不足以单独解关。
- 然后才寻找目标物理 Assistant 消息（或唯一 turn/attempt）与 API request_id 的原始**因果绑定**。不得再靠时间最近、同 session、`v2EventClaimId` 或 2/4/2 软时间筛选。
- 最后验证真实 Provider dispatch 的模型、参数、动态 Session/summary/RAG/locale/flags 和前后清理消息原始字节／可靠字节等价证明。
- **停止条件：** 无授权的可信历史发布来源，或缺 target↔request 因果证据，或 Provider 完整字节不可得，则 G2 HOLD；不 SSH 扫生产、不读取异常快照或敏感历史日志、不伪造部署区间 manifest。

### P4 — G3：仅在 G1/G2 独立批准之后

- 仅对**现有最多五世界／20 回复上限内**且未被排除的既定候选进行双 Reviewer + Owner 逐项审核；不自动训练、冻结 v0.4、模型晋升或扩样。
- `R58_ROUND1_PILOT_COMPLETION_SAFE.json` 只能在真实首轮审核结束、独立验收后产生；`R58_ROUND1_PILOT_REVIEW_COMPLETE` 与 Owner 后续批准扩大样本是**两个独立动作**。

## 5. 后续 Agent 直接使用的来源索引

StoryForge 基准 HEAD `62d7dcd847a7dd485c40a63fbba0d1855bc3135f`：

- `docs/handoffs/R58_NEW_AGENT_HANDOFF_SAFE_20261031.md`
- `docs/handoffs/R58_NEW_AGENT_STATE_SAFE_20261031.json`
- `docs/handoffs/R58_NEW_AGENT_START_PROMPT_SAFE_20261031.md`
- `docs/evidence/R58_OWNER_V02_80_PASS_RUFF_ZERO_POSTFIX_SAFE_20261031.json`
- `docs/evidence/R58_G1_G2_SKILL_V02_READINESS_MATRIX_SAFE_20261031.json`
- `docs/evidence/R58_G1_G2_EVIDENCE_RECOVERY_STOP_RULES_SAFE_20261031.md`
- `docs/evidence/R58_G1_KNOWN_FIVE_JOB_CURRENT_PRIMARY_INPUTS_CROSSCHECK_SAFE_20261031.json`
- `docs/evidence/R58_OWNER_V02_61_PASS_EXISTING_PRIORITY_CROSSLINK_SAFE_20261031.json`
- `docs/evidence/R58_G2_PINNED_REQUEST_ID_PERSISTENCE_SOURCE_AUDIT_SAFE_20261031.json`
- `docs/evidence/R58_G2_DEPLOYMENT_SHA_SOURCE_PROVENANCE_SAFE_20261031.json`
- `docs/evidence/R58_G2_DEPLOYMENT_PROVENANCE_RECOVERY_RUNBOOK_SAFE_20261031.md`
- `docs/HF_RUN_REGISTRY.md`（已知 baseline 工件登记，不等于优先 CANCELED Job）

独立源码 pin：`sunxu/RolePlay@e9fe29c42434caeb0bac5acc91845ab4741ecb2b`。**GitHub 源码 pin ≠ 生产时点部署证据**。

## 6. 本轮未实施操作

未访问私有训练样本、R50 题目或候选正文；未访问 Owner 私有目录/原始 Trainer/Provider 请求；未 SSH 生产主机；未启动 HF CPU/GPU Job、训练或推理；未修改 Skill v0.1/v0.2、Dataset v0.4、`main`，未关闭/合并 PR；未重跑已通过的 80 项 Owner Mac 测试。本文件自身只是 **SAFE 状态增量归档**，没有 G1/G2 清关效力。

**最终准入状态：`G1=HOLD; G2=HOLD; G3=NOT_STARTED; train=0; validation=0; teacher=0; expansion_allowed=false`。**
