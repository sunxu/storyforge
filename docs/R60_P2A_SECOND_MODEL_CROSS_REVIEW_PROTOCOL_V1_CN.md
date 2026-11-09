# R60 P2-A 第二模型独立交叉审核协议 v1

> **当前权威状态（2026-11-10；覆盖下方未标明日期的旧 P2-A 待办叙述）**  
> **P0 PASS、P1 PASS、P2-A COMPLETE；P2-B NOT STARTED、P3 NOT STARTED、P4/P6 NOT AUTHORIZED。** Owner Mac 官方 Verifier SAFE 为 `OWNER_REVIEW_COMPLETE__SEMANTIC_HOLDS_PRESERVED`：20/20 个案例、60/60 条语义复核，58 `SUPPORTS_VERDICT`、1 `INSUFFICIENT_CONTEXT`、1 `SEMANTIC_ENTAILMENT_NOT_ESTABLISHED_HOLD`，`quality_v1_admitted=0`、`training_authorized=false`、`gpu_started=false`、`owner_identity_cryptographically_attested=false`。两项语义 HOLD 是真实审核结果，不得通过改判消除。  
> **新 Agent 只从 P2-B 独立 30/90 held-out 参照集工程及 P3 三模型 CPU 预检接手，不重做 P0/P1/P2-A。** 最终官方 SAFE 与阶段收尾详见 [Issue #28 验收回帖](https://github.com/sunxu/storyforge/issues/28#issuecomment-6745451510)，执行提示词见 [2026-11-10 新 Agent 启动指令](R60_NEXT_AGENT_START_PROMPT_20261110_CN.md)。  
> PR #25 在本次核验时 Open/Draft，base `r60/canonical-a-v3-binding`；2026-11-10 核验前 HEAD `352fd48d50f5f24402b2bef849240833f6ab270e` 对应五组 Actions 均 completed/success。**本次文档提交会再次推进 HEAD；新 Agent 必须核对最新 HEAD 与 CI，不得沿用此快照。** 下方“P2-A 尚未开始”“下一步生成 20/60”“P2-A HOLD”等日期较早的章节均仅为历史记录，不得作为执行入口。  
> P2-A 80 个证据 locator 与 39 条历史完整性确认只落在派生文件，原件未修改；正式结论不等于训练准入。P2-B Locked20 + Severe10 不与 Development20 混包，不向模型泄露 held-out Owner labels。P4 GPU、P6 1000 条批量审核、SFT 均需单独授权。


## 2026-11-10 收尾与后续交接（唯一最新行动入口）

| 阶段 | 结果 | 新 Agent 工作 |
|---|---|---|
| P0 | PASS | 只读复用冻结集，不重跑、不重新分组 |
| P1 | PASS | 复用 Rubric v2.1 / Schema / Prompt / regression |
| P2-A Development20 | **COMPLETE**；20 cases + 60 checks；语义 58/1/1，保留两项 HOLD | 冻结留证，不重审、不修改原始 verdict |
| P2-B Locked20 + Severe10 | **NOT STARTED** | 独立 30 results / 90 semantic checks Builder + Verifier；synthetic PASS；Owner 私有 labels 与 model inference 严格隔离 |
| P3 三模型 | **NOT STARTED** | Qwen3/GLM-4/GLM-Z1 精确 revision 与 CPU tokenizer/template/collator/预算 preflight；实际型号差异须明示 |
| P4/P6 | **NOT AUTHORIZED** | 不启动 GPU/HF 推理/1000 批量审核/SFT |

### 接手行动与门禁

1. 阅读 [新 Agent 提示词](R60_NEXT_AGENT_START_PROMPT_20261110_CN.md)，实时核对 PR #25、Issues #26/#28、当前分支 SHA 与该 SHA 的五组 CI；不要将历史快照当当前结果。
2. 复用 P2-A 契约与测试实现 P2-B **独立版本化** 30/90 Builder/Verifier（旧官方 20/60 Verifier 不适用于 30/90）。先 synthetic/CPU 工程，后 Owner 私有 30 项裁决；真实不足继续 HOLD，不得静默改标签。Locked20/Severe10 的 Owner labels、ID Map、旧判断不得进入三模型推理输入。
3. 在不阻塞 P2-B 的前提下，并行准备 P3 只读三模型版本固定和 CPU 预检。CPU 资源如收费先授权；未经允许不发私有文本到外部服务；不启动 GPU/SFT。
4. 提交代码/测试/脱敏 SAFE 和文档；私有正文、映射、逐案证据、密钥仅留 Owner 私有目录。无 Owner Mac 连接则不假称已运行，给出最短受控指令。
5. Issue #28 维持 OPEN；PR #25 维持 Draft，合并另行审查。P2-A 已验收只是这一阶段的闭环，不是自动训练准入。

### P2-A 最终可复核的 SAFE（不含私人内容）

```json
{
  "schema": "storyforge_r60_owner_adjudication_results_safe_v2",
  "status": "OWNER_REVIEW_COMPLETE__SEMANTIC_HOLDS_PRESERVED",
  "cases_verified": 20,
  "semantic_checks_verified": 60,
  "semantic_supported_count": 58,
  "semantic_insufficient_context_count": 1,
  "semantic_not_established_count": 1,
  "owner_identity_cryptographically_attested": false,
  "quality_v1_admitted": 0,
  "training_authorized": false,
  "gpu_started": false,
  "private_values_emitted": false
}
```

**说明：** 此 SAFE 为 Owner Mac 实际运行仓库官方 `scripts/r60_owner_adjudication_verify_v2.py` 的用户回执，非 GitHub CI 运行；不发布原始私有 JSONL。80 条 evidence locators、39 条 Owner 已批准的 history completeness、4 处 SUPPORTED Player Agency basis 类型均只在派生副本规范化。保留 58/1/1，未做 cryptographic identity attestation。旧模型的 AI Advisory 不冒充 Owner。

---

日期：2026-11-09

## 目的

对 Development-20 的 60 个维度判断增加第二模型独立交叉审核，识别第一模型的潜在错误、遗漏和上下文问题。第二模型输出只作为 `AI_CROSS_REVIEW_ADVISORY_NOT_OWNER`，不能替代 Owner 最终语义复核，也不能直接写入官方 `OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl`。

## 已确认事实

- 原 60 条 semantic checks 是 Owner AI 生成，未经 Owner 逐项最终确认。
- 原文件缺少 reviewer_role、reviewer_ref、rubric_version，且额外包含 unresolved_context。
- 原 AI checks 不符合官方七字段合同，也不能通过回溯性元数据补齐伪装为 Owner 独立复核。
- 原 AI checks、35 条 AI history advisory、4 条 AI history advisory 均保持原样封存，只作参考，不作为第二模型输入。
- 原始 20 条 Owner results 是第二模型的核对对象；模型必须独立判断 Owner verdict/evidence 是否成立，不得默认其正确。

## 第二模型输入

Builder 仅读取：
1. `OWNER_ADJUDICATION_BLIND_PACKETS_PRIVATE.jsonl`
2. `OWNER_ADJUDICATION_RESULTS_PRIVATE.jsonl`
3. 公开 Rubric v2.1 文件

Builder 明确不读取：
- `OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl`
- `OWNER_HISTORY_COMPLETENESS_AI_REVIEW_35_PRIVATE.jsonl`
- `OWNER_SUPPORTED_HISTORY_COMPLETENESS_AI_REVIEW_4_PRIVATE.jsonl)
- 任何第一模型的输出或建议

Builder 为 20 个案例生成全新 blind IDs 并重新打乱顺序。模型包只含 visible_history、target_text、verified_world_components，以及每个维度待核对的 Owner verdict、evidence、rule_basis、context_coverage。旧 calibration IDs 与 ID map 不进入模型包；ID map 单独留在 Owner 私有目录。

## 模型选择与执行

- 使用与第一模型不同的模型提供方/模型家族。可选择 Claude 或 Gemini 的可用模型；实际模型 ID、版本、调用日期、参数和服务端返回的完成状态必须由执行者记录。
- 不宣称不同供应商即天然无偏；交叉审核仍是 AI Advisory。
- 同一批 20 案例 × 3 维度，共 60 项；必须完整覆盖。
- 模型必须看到完整上下文和对应 Owner verdict/evidence，但不得看到第一模型的 semantic checks 或 AI Advisory。
- 若外部模型服务的隐私/数据处理条件未获用户确认，不得上传私有故事正文；可先只生成本地私有包并暂停外发。
- 不使用 P3 模型训练/GPU/HF Job；本步骤是外部模型辅助内容审核，不启动训练任务。

## 第二模型输出合同

每个 `blind_id × dimension` 恰好一行，输出 JSONL：
- `blind_id`
- `dimension`
- `reviewer_type=AI_CROSS_REVIEW_ADVISORY_NOT_OWNER`
- `conclusion=SUPPORTS_VERDICT | DOES_NOT_SUPPORT_VERDICT | INSUFFICIENT_CONTEXT`
- `reviewed_evidence_indexes`
- `reasoning_summary`
- `unresolved_context`

所有引用索引必须完整覆盖该维度全部 evidence；不得只挑选有利证据。不得更改 Owner verdict。不得因缺少来源、版权、权利、隐私、授权或数据隔离材料而 HOLD；故事内玩家明确拒绝/同意/选择边界、故事硬规则和安全边界仍是内容审核依据。

## Owner 最终复核

第二模型完成后：
1. 将 60 条 AI Advisory 与原始 Owner results、第一模型 Advisory 作差异分析。
2. 按维度列出一致、分歧、第二模型新发现的遗漏、HOLD。
3. Owner 对全部 60 项作最终判断；至少对所有模型分歧项逐条阅读原文、证据和上下文。
4. 只有 Owner 实际完成最终复核的项目，才可生成官方语义复核记录；每行记录实际审核时间、Owner role/ref、rubric version、完整 evidence indexes 和 Owner 自己的 reasoning。
5. 不能复制第二模型 conclusion/reasoning 后直接标记为 Owner。Owner 必须形成自己的判断和理由。
6. 所有未解决项保留 HOLD。AI 一致率不是通过门槛。

## 版本与隔离

- 第二模型私有输出目录 create-only，目录 0700，文件 0600。
- 私有 manifest 绑定原始 packets/results/rubric、第二模型输入包、ID map、prompt 的 SHA-256。
- SAFE 只记录聚合计数和边界，不输出正文、case IDs、blind IDs、reviewer refs、私有 SHA。
- 第二模型结果不得进入模型训练、Prompt 开发或 P2-B held-out labels。
- 本协议不改变 P2-A 20/60 官方 verifier 合同，也不解锁 Locked20 / Severe10。


## OpenAI-compatible CLI Proxy 批量调用实现（2026-11-09）

新增可复用客户端：`scripts/r60_p2a_openai_compatible_review_client.py`。

### 模型与接口配置

- 默认模型别名：`claude-opus-5-5`（来自 Owner 提供的 CLI Proxy 可用模型清单；执行时仍须核对代理实际接受的 model ID）。
- 协议：OpenAI Chat Completions。
- 默认非流式：`stream=false`。目前流式能力未知，因此不依赖流式接口。
- 远程代理必须使用 HTTPS。
- Base URL 通过 `CLI_PROXY_BASE_URL` 提供，支持传入代理根路径、`/v1` 或完整 `/chat/completions` URL。
- API Key 仅从 `CLI_PROXY_API_KEY` 或 `OPENAI_API_KEY` 环境变量读取；不得写入命令行参数、文件、日志或 Git。
- 如果代理的实际模型 ID 与 UI 别名不同，设置 `CLI_PROXY_MODEL`。SAFE/manifest 记录实际传入的 model 字段。

### 批量执行与验证

- 固定 5 案例/批，共 4 批，每批 15 个维度判断。
- 每批使用不发送 temperature 参数（Claude Opus 5.5 已返回 temperature deprecated 错误），默认 max_tokens 12000，timeout 300 秒。
- 只对网络错误及 HTTP 408/409/425/429/5xx 做有限重试；不对格式错误伪装成功。
- 已验证批次结果以 0600 私有 JSONL 保存；支持 `--resume`，重启时先验证并复用已完成批次。
- 必须严格验证 60 个 blind_id × dimension 唯一组合、字段集合、枚举、Reviewer 类型和每项完整 evidence index 覆盖。
- 不接受 Owner 身份字段，不会把 AI Advisory 转换为 Owner 结果。
- 预检默认不发出外部请求；实际外发必须同时显式传入 `--execute --allow-private-data-egress`。
- 不读取 ID Map，不读取旧 AI semantic checks 或旧 AI Advisory。

### Owner Mac 配置与命令

在 Owner Mac 私有 shell 环境中设置，不要把密钥发到聊天或写入项目：

```bash
export CLI_PROXY_BASE_URL='https://你的代理域名/v1'
export CLI_PROXY_API_KEY='在本机安全注入的密钥'
export CLI_PROXY_MODEL='claude-opus-5-5'
```

建议输出目录位于第二模型盲包目录之下，且父目录必须为 0700：

```bash
PRIVATE="$HOME/.local/share/storyforge/r60/private"
IN="$PRIVATE/owner-adjudication-dev20-second-model-cross-review-20261109"
OUT="$IN/model-run-claude-opus-5-5-20261109"
RUN="/Users/keedle/workspace/storyforge-r60-p2a-owner-runner"

python3 "$RUN/scripts/r60_p2a_openai_compatible_review_client.py" \
  --input-dir "$IN" --output-dir "$OUT"

# 预检 PASS 后才执行真实外部调用；首次预检已创建目录和私有 manifest，
# 因此执行时需加 --resume。
python3 "$RUN/scripts/r60_p2a_openai_compatible_review_client.py" \
  --input-dir "$IN" --output-dir "$OUT" \
  --execute --allow-private-data-egress --resume
```

SAFE 成功状态：`CROSS_REVIEW_MODEL_CALLS_COMPLETE__ADVISORY_ONLY`。若中断，使用相同输入、模型和 endpoint 加 `--resume`。任何输入 SHA、模型或 endpoint origin 不匹配均停止，不覆盖已有私有结果。

### 执行边界

本工具仅进行外部模型内容审核，不运行 GPU、HF Job、SFT，不更改 Owner results、原始 semantic checks、Gold72 分组或 P2-B held-out 数据。即使 60 项全部得到有效 AI 输出，P2-A 仍须由 Owner 独立完成最终语义复核。


### 4Router 模型目录核验（2026-11-09）

Owner 提供的 `GET https://4router.net/v1/models` 返回列表中明确包含 `claude-opus-5-5`，且该模型的 `supported_endpoint_types` 包含 `openai`。因此客户端默认 model ID 已从未经目录证实的 `claude-opus-5-5-high` 更正为 `claude-opus-5-5`。

目录未返回独立的 `claude-opus-5-5-high` ID，也未证明 OpenAI-compatible 接口支持名为 `high` 的推理等级参数。当前客户端不擅自发送该参数；先以标准非流式 Chat Completions 做单次最小连通性/模型调用验证，再决定是否存在服务商专属的 High 配置。模型目录出现该 ID 只证明列出可用，不等于真实调用已成功。


### 2026-11-09：HTTP 4xx 私有诊断补强

首次 Claude Opus 5.5 批量请求返回 `PROXY_HTTP_400`。此前客户端只保留状态码，未保留服务端错误体，无法区分参数拒绝、上下文限制或代理侧策略拒绝。

现已补强客户端：每次 HTTP 错误响应体写入对应批次的私有文件 `BATCH_NN_ATTEMPT_MM_HTTP_ERROR_PRIVATE.json`（0600、独占创建）；SAFE reason 仅暴露 HTTP 状态、error type/code/param，不暴露服务端 message、请求正文或密钥。每次重试使用独立文件名，保留诊断历史。不得将该私有错误文件原文贴到公开 Issue；如需分享，仅提供安全字段，或经检查后删去任何回显的私有正文。

下一次执行使用同一输出目录和 `--resume`。若再次返回 400，先读取本地错误文件中的 `error.type`、`error.code`、`error.param`，必要时在 Owner Mac 本地检查 message；不要盲目修改请求参数。既有授权仍仅覆盖同一 20 条 Development 盲包发往 4Router。


### 2026-11-09：4Router Claude system prompt 格式兼容修复

Owner 的本地 HTTP 400 message 明确指出：`messages.0` 不允许作为初始 system prompt，必须使用顶层 `system` 参数。已修复客户端请求体：审核指令放入顶层 `system`，`messages` 仅包含 user 消息；模型、批次内容、max_tokens、stream=false 和不发送 temperature 的约束保持不变。新增合成测试，断言顶层 system 存在且 messages 不含 system role。

下一步必须先更新 Owner Mac 执行 worktree 至包含该修复的提交，并运行本地测试/只读检查。随后使用原输出目录 `--resume`：失败批次的旧 HTTP error 文件保留，批次 1 会重新请求；任何已完成且验证通过的批次继续复用。当前修复尚未经过 CI，也尚未证明真实请求成功。未经再次检查，不要扩大外发范围。


## 2026-11-09：Claude Opus 5.5 第二模型交叉审核调用完成（Advisory only）

Owner 提交的真实 SAFE 回执：

- status：`CROSS_REVIEW_MODEL_CALLS_COMPLETE__ADVISORY_ONLY`
- model：`claude-opus-5-5`
- cases：20；dimensions：60；rows_validated：60；batches：4/4
- reviewer_type：`AI_CROSS_REVIEW_ADVISORY_NOT_OWNER`
- private_data_egress：true（仅此前明确授权的 Development-20 盲包发往 4Router）
- owner_review_completed：false
- gpu_started：false；training_authorized：false；private_values_emitted：false

客户端顶层 `system` 兼容修复对应分支 HEAD `1d337afcea22a52ec0b553b730d3f9b2200fa5c5` 的五项 Actions 均 completed/success：CI、R60 HF Runtime CI、R60 HF CPU dependency profiles、Gold Quality Pipeline、R58 scoped synthetic。该结果验证代码/合成回归，不等于 Owner 内容裁决通过。

**当前唯一下一步：Owner 对 60 项 Claude Advisory 与原始 20 条 Owner results / Rubric v2.1 逐项核对，形成自己的 60 项最终语义判断。** Claude 结论不能自动采纳、不能回填成 Owner semantic checks；逐项保留分歧和真实 HOLD。Owner 最终记录须使用正式七字段合同并由官方 verifier 验证。P2-A 在 Owner 60 项最终复核及官方 verifier PASS 前仍为 HOLD；不启动 P2-B、P3、GPU/HF Job、1000 条审核或 SFT。


## Owner 实际复核操作指南（2026-11-09）

### 推荐工作方式：分批逐项确认，不要求 Owner 手工编辑 JSONL

Owner 最终复核必须覆盖 20 案例 × 3 维度 = 60 项。建议分为 12 组，每组 5 项；每项只讨论一个维度，避免将同一案例三个维度混为一个整体结论。

每项复核时，按以下顺序阅读：
1. 完整 `visible_history`，确认玩家此前的明确选择/拒绝/同意，以及必要故事上下文。
2. `target_text`，确认本次实际被判断的行为和行为主体。
3. `verified_world_components`，仅在 Hard Rule 判断中使用实际提供且适用的规则/世界组件；不得补造缺失规则。
4. Owner 原始 verdict、该维全部 evidence、rule_basis、context_coverage、missing_context。
5. Claude 第二模型 Advisory 的结论、理由和 unresolved_context。先独立形成自己的判断，再看 Claude 意见；若已看到 Claude 意见，必须特别避免顺从偏差，重新回到原文核对。

### 每一项 Owner 必须回答

- 我是否逐条检查了该维度全部 evidence，而不是只看一条有利引用？
- 引文是否准确定位到可见历史/目标/已验证世界组件？
- 引文的实际语义是否足以支持 Owner verdict？
- 是否存在反向证据、被忽略的玩家边界、适用规则或必要上下文？
- 我自己的最终语义复核结论是什么？理由是什么？

### 结论选择

| Owner conclusion | 适用情况 | 后续处理 |
|---|---|---|
| `SUPPORTS_VERDICT` | 全部 evidence 已检查，且语义上支持该维 Owner verdict | 该项语义复核可通过；不代表案例 Quality PASS |
| `DOES_NOT_SUPPORT_VERDICT` | 引文存在但不蕴含 verdict，或证据之间冲突 | 保留 HOLD；不得在 semantic check 中静默改写原 verdict |
| `INSUFFICIENT_CONTEXT` | 缺少判断所必需的历史、玩家边界、适用规则或安全情境 | 保留 HOLD；只有原 Owner verdict 也是 `INSUFFICIENT_CONTEXT` 时，才符合对应验证器分支 |

若 Owner 认为原始 verdict 本身应改变，先停止该项的语义复核并单独记录“建议重新裁决”的原因；不得把改 verdict 与 semantic entailment check 混为一件事，也不得直接修改原始结果文件。由版本化修订流程另行处理。

### 记录规则

- 每个维度一条正式记录；共 60 条。
- 外层恰好四字段：`calibration_id`、`dimension`、`reviewed_at_utc`、`check`。
- 内层恰好七字段，严格遵守本任务书 8.23.2。
- `reviewed_evidence_indexes` 必须完整覆盖该维全部 evidence 索引；不得只记录支持结论的引用。
- `reasoning_summary` 必须写 Owner 自己的理由（12–1200 字符），不能复制 Claude 文本或只写“同意”。
- `reviewer_role=OWNER_INDEPENDENT`；60 行使用同一个 8–128 字符 `reviewer_ref`。该字段是记录标识，不是密码学身份认证。
- 每行 `reviewed_at_utc` 记录真实复核时间，UTC offset 为零。
- 原始 packets、Owner results、Claude Advisory 均只读；正式 Owner checks 以 create-only 新文件写入，权限 0600，父目录 0700。

### 如何与 ChatGPT 协作（可选）

若 Owner 希望逐批在 ChatGPT 中查看，需由 Owner 主动上传以下三份私有材料：
- `AI_CROSS_REVIEW_PACKETS_PRIVATE.jsonl`（包含盲化后的完整上下文和待核对 Owner verdict/evidence）；
- `AI_CROSS_REVIEW_RESULTS_PRIVATE.jsonl`（Claude 60 项 Advisory）；
- `RUBRIC_V2_1_PRIVATE.md`（本批绑定的 Rubric 副本）。

**不要上传** `AI_CROSS_REVIEW_ID_MAP_PRIVATE.json`、原始 calibration ID 映射、P0 manifest、Locked20/Severe10 或任何第一模型历史 AI checks。上述三份文件足以按第二模型 blind_id 对齐上下文、Owner 依据和 Claude Advisory。若文件内容不完整或字段无法对齐，先 HOLD，不猜测映射。

ChatGPT 可以整理每项证据、解释 Rubric、指出 Claude 与原证据的冲突并提出建议；但 ChatGPT 的建议仍是 AI 辅助。Owner 必须自己选择最终 conclusion，并亲自提供 reasoning。不得将 ChatGPT 输出自动标记为 Owner 复核。

建议按 5 项一组进行交互。每组完成后由 Owner 明确确认 5 项结论及理由，再由本地工具生成对应正式记录；未确认项目保持未完成。完成 60 项后，运行官方 `scripts/r60_owner_adjudication_verify_v2.py`，如实保留所有 semantic HOLD。结构验证通过不等于语义全部通过。
