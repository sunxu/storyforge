> **执行入口已迁移（2026-11-10）：** 本文件中的 P3 CPU-only 预检任务已完成，不再是当前待办。请勿按下方历史提示从 P3 重跑。当前唯一有效的接手提示词是 [P4 Worker CLI 工程验收提示词](R60_P4_NEXT_AGENT_START_PROMPT_20261110_CN.md)，完整任务书是 [P4 下一阶段接手任务书](R60_P4_NEXT_AGENT_HANDOFF_TASKBOOK_20261110_CN.md)。当前目标为 P4-A Worker CLI/bootstrap CPU-only 端到端验收 → P4-B Owner Mac CLI 执行包 → P4-C 32K 资源预算 → P4-D 最终 Profile Freeze Review。HF 403/OAuth/Bucket 问题按 Owner 要求暂停；ChatGPT 不提交 HF Job、不测试 Bucket、不修改 OAuth，HF 任务由 Owner 在 Mac CLI 执行。下方内容仅保留历史背景，不得作为当前行动指令。

---

# StoryForge R60 下一阶段 Agent 接手提示词（P2-B 已验收，P3 CPU-only）

版本：v2.0；更新：2026-11-10。适用仓库：`sunxu/storyforge`。

> 本提示词覆盖旧版本中“P2-B Owner review pending / Safety 21、22 保留 SUPPORTED 且等待规则 ID / 官方 Verifier 未运行”等过时指令。P2-B 官方 Verifier 已通过；不要重做 P0、P1、P2-A 或 P2-B。

## 1. 你的任务

你现在接手 StoryForge R60 Quality 校准与模型评估项目。直接使用已连接的 GitHub 工具推进仓库代码、测试、文档与 Issue；不要停留在重写计划。当前唯一主线是 **完成 P3 三模型 CPU-only Tokenizer / Chat Template / token-budget 预检**，并为之后 P4 三模型配对实验准备可复现 profile 与预算。

## 2. 仓库和关联对象

- Repository：`sunxu/storyforge`
- Branch：`r60/gold192-history-v3-adapter`
- PR：[#25](https://github.com/sunxu/storyforge/pull/25)，base `r60/canonical-a-v3-binding`，保持 Open / Draft。
- 主线 Issue：[#26](https://github.com/sunxu/storyforge/issues/26)。
- 执行 Issue：[#28](https://github.com/sunxu/storyforge/issues/28)，保持 OPEN。
- Owner Mac worktree：`/Users/keedle/workspace/storyforge-r60-ledger-diagnostics`。
- Owner 私有根目录：`$HOME/.local/share/storyforge/r60/private/`。除非有获准的受控连接工具，不要假设你可以直接访问 Owner Mac；需要本地执行时给出最短、可复制的命令和 SAFE 回传要求。

**启动第一步必须实时核对** PR #25 head/base/draft、分支 HEAD、Issue #26/#28 和当前精确 HEAD 对应的五组 Actions：CI、R60 HF Runtime CI、R60 HF CPU dependency profiles、Gold Quality Pipeline、R58 scoped synthetic。不要复用任何历史 HEAD 的 CI 结果；不要 reset、force-push、merge 或关闭 PR。

## 3. 已完成阶段（不可重做）

- **P0 PASS**：Gold72=40，Development20 + Locked Regression20；R60 Severe10=10；按案例分割，不要求 Story 互斥；冻结集合和交集结果不得重分组。
- **P1 PASS**：Rubric v2.1 / Schema / Prompt / synthetic regression / 旧 v3 兼容已通过。唯一标准 `r60_severity_rubric_v2_1`。不修改 Rubric。
- **P2-A COMPLETE**：20/20 Owner Results + 60/60 semantic checks 官方验证；58 支持、1 上下文不足、1 语义未建立，保留 HOLD。不得重做或修改。
- **P2-B COMPLETE（官方 Verifier）**：30/30 cases、90/90 semantic checks；SAFE：
  - schema：`storyforge_r60_p2b_owner_results_safe_v1`
  - status：`P2B_OWNER_REVIEW_COMPLETE__SEMANTIC_HOLDS_PRESERVED`
  - semantic_supported_count=57
  - semantic_insufficient_context_count=33
  - semantic_not_established_count=0
  - owner_identity_cryptographically_attested=false
  - private_values_emitted=false
  - quality_v1_admitted=0；training_authorized=false；gpu_started=false
- P2-B 的 57/33/0 是语义复核状态，不是三维 Verdict 分布、案例质量 PASS 或训练准入数。Hard Rule 30 项均 INSUFFICIENT_CONTEXT；Player Agency 3 SUPPORTED / 27 NOT_SUPPORTED；Safety 最终 0 SUPPORTED / 27 NOT_SUPPORTED / 3 INSUFFICIENT_CONTEXT。
- Safety 第21、22条：Owner 二次确认均改为 INSUFFICIENT_CONTEXT；原始 SUPPORTED 裁决及修订审计记录保留。仅修改这两个 Safety 维度，其他88个维度项不变；Rubric v2.1 未修改；未臆造 Rule ID。不得再次改写。
- Owner 身份未密码学认证；不要宣称远端模型身份或独立身份认证。
- P2-B 的私有 packets、ID Map、逐案 Owner results、语义证据不上传 GitHub，不进入 P3 模型输入。

## 4. P3 已有静态 Revision（精确固定，不可改用 main）

| Role | Model | Revision |
|---|---|---|
| A | `Qwen/Qwen3-32B` | `9216db5781bf21249d130ec9da846c4624c16137` |
| B | `zai-org/GLM-4-32B-0414` | `8dea913c41b543527c2860fb6f3c15c202f24aeb` |
| Challenger | `zai-org/GLM-Z1-32B-0414` | `8eb2858992c1f749e2a6d4075455decc2484722d` |

静态元数据已核对，尚未下载 tokenizer 文件、计算本地文件 SHA、执行 tokenizer/template 或模型推理。保守共同原生上下文上限为 32768 tokens；不得把 tokenizer 的 128k/131k model_max_length 当作模型原生上下文证据。

### 已知 profile 约束

- Qwen：Thinking 必须显式启用；模型卡建议 temperature=0.6、top_p=0.95、top_k=20、min_p=0；Thinking 模式不应擅自改成 greedy。
- GLM-4：generation_config 未固定 sampling 参数；不得照搬 Qwen 参数，需明确模型专属 profile。
- GLM-Z1：模型卡 sampling 表与 inference 示例冲突（sampling vs do_sample=false greedy）；必须先给 Owner 决策依据，未决前 profile 不冻结，不可擅自选择。
- GLM-4 与 GLM-Z1 同属 GLM4 架构家族，不是两个独立家族的投票。
- 运行时基线需复核：transformers==4.57.1、sentencepiece==0.2.1、jinja2==3.1.6。R58 已证明缺 Jinja2 会造成 Chat Template ImportError，R60 不得重复此故障。

## 5. P3 具体执行清单

1. 阅读并核对：
   - 本提示词；
   - `docs/R60_NEXT_AGENT_HANDOFF_TASKBOOK_20261109_CN.md`；
   - `docs/R60_CALIBRATION_EXECUTION_TASKBOOK_20261108_CN.md`；
   - `docs/R60_CALIBRATION_NEXT_AGENT_HANDOFF_20261108_CN.md`；
   - `docs/R60_HANDOFF_PACKAGE_INDEX_20261109_CN.md`；
   - `docs/R60_P3_MODEL_STATIC_PREFLIGHT_20261110_CN.md`；
   - `docs/R60_SEVERITY_EVIDENCE_RUBRIC_V2_1_CN.md`。
2. 检查并复用现有 HF runtime、CPU dependency profiles、hash lock 和 tokenizer/chat-template 测试；不重复开发已有功能。
3. 在本地 CPU 环境仅下载三个固定 revision 的 tokenizer/config/template 必要文件，**不下载模型权重**；记录每个文件的 SHA-256。
4. 对三模型执行 tokenizer load 和 chat-template render：中文多轮消息、system/user/assistant 角色、generation prompt、Qwen Thinking 开关、GLM-Z1 think 前缀与历史 think 内容处理。
5. 对 GLM tokenizer embedded template 与独立 `chat_template.jinja` 实际比较；不一致即 HOLD，明确选择并 pin 实际运行时来源。
6. 复核依赖版本与 pip check；不初始化 CUDA、不加载模型权重、不执行模型 inference。
7. 仅用 synthetic 数据测试 32768 context ceiling、共享 prompt/output budget、90 输入 token 预算、截断行为、finish_reason、输出 schema 和超限失败策略。禁止读取 P2-B 私有文本、Owner labels 或 ID Map。
8. 固定每模型的 revision、tokenizer SHA、template SHA、prompt/rubric SHA、runtime/package versions、generation 参数、seed、输出预算、stop/finish reason 规则。GLM-Z1 冲突未解决时保持未冻结。
9. 生成 CPU-only SAFE 与复现命令；更新任务书、执行任务书、交接总览、索引、P3 静态预检文档及 Issue #28。
10. P3 完成后提交 P4 30 条严格配对三模型评估方案与资源预算，向 Owner 请求单独授权；不得自动启动 GPU/HF Job。

## 6. 严格禁止事项

- 不重做 P0/P1/P2-A/P2-B，不修改历史 Owner Verdict，不改 Rubric v2.1。
- 不向模型或外部服务发送 P2-B held-out 文本、Owner labels、ID Map。
- 不读取 R50 私有正文，不修改 RolePlay 或生产数据库。
- 不启动 GPU、模型 inference、付费 HF Job、1000 条批量审核或 SFT；CPU 云资源如收费也必须先获得明确授权。
- 不把 57/33/0 说成 57 条 Quality PASS；不把 Owner SAFE 当作密码学身份认证。
- 不上传私有正文、blind IDs、crosswalk、逐案审核文件、token、DSN。
- PR #25 保持 Draft；Issue #28 保持 OPEN；不得自动合并。

## 7. 交付和汇报

每次工作必须给出真实命令、实际下载文件与 SHA、测试/SAFE 输出、commit SHA、修改文件、五组 CI 结果、资源/费用、未解决 HOLD。未执行步骤不得报告 PASS。P3 完成后只申请 P4 授权，不越权执行。

**现在开始：刷新 GitHub 实际状态 → 阅读当前代码与文档 → 直接实施 P3 CPU-only tokenizer/template/token-budget 预检。**

## 2026-11-10 权威更新：ChatGPT Hugging Face OAuth / Bucket RW 故障

- 插件：Hugging Face Plugin v0.1.4，关联日期 2026-11-04，Version ID `asdk_app_v_225a5afb50248191aaab67016a94edc0`，OAuth Application ID `asdk_app_6ac752d4c640819191c206f9cb0dafad`，状态 RELEASED。
- ChatGPT `hf_whoami`：账号 `greenkeedle`，`adradar` 组织角色 `write`；OAuth scopes 为 `openid profile read-mcp read-repos jobs contribute-repos inference-api`。
- ChatGPT 连接器可创建并执行无 Volume CPU Job；提交 `hf://buckets/adradar/storyforge-training:/output` RW Job 返回 HTTP 403。
- Owner Mac CLI 使用同一 `adradar` namespace、`python:3.12`、`cpu-basic` 和相同默认 RW volume 成功完成 Job `6af2ee90ab34849891ab2f6e`：写入 `/output/.p4-rw-probe`、读回 `PASS`、删除文件。
- ChatGPT 无 Volume CPU Job `6af2ec43ab34849891ab279c` 成功。RO Job `6af2ec64ab34849891ab27f8` 仅有提交接受记录，没有可用执行/读回证据，不得写成 RO 端到端 PASS。
- Owner 提供的 Bucket Settings 页面显示 `adradar/storyforge-training` 为组织 Private Bucket，组织成员可查看和上传；未修改 ACL、可见性或 Trusted Publishers。

### 诊断边界
证据将故障收敛到 ChatGPT HF 连接器的 Bucket RW 提交/授权链路，而非 Bucket 普遍不可写、组织余额不足或 Jobs 创建权限整体失效。当前 OAuth scope 缺少 `write-repos` / 专用 Bucket write scope 是待验证假设，不是已证实根因；公开文档没有明确证明其必然导致 Jobs Bucket RW 403。仍需 HF 检查该 OAuth App 的 capability、组织 grant、请求序列化及 403 服务端拒绝原因。

### 后续执行规则
- ChatGPT 直连 Bucket RW：`BLOCKED_403`；P4 私有输出持久化保持 HOLD。Mac CLI 同 Bucket RW：PASS，只是 Owner 受控临时路径，不代表 ChatGPT 链路通过。
- 要求 Hugging Face 检查 OAuth App `asdk_app_6ac752d4c640819191c206f9cb0dafad`（Plugin v0.1.4）是否允许挂载既有组织私有 Bucket RW、`adradar` grant 是否完整，并解释 403。
- 不切个人 namespace，不索取长期 PAT，不修改 Bucket ACL，不配置 Trusted Publishers，不将私有生成正文写入 GitHub / Actions logs / SAFE。
- 不盲目重复提交 RW Job；等待 HF 答复或连接器修复。该问题不影响 CPU Freeze Review SAFE，但阻止正式评估私有输出通道验收。
- 后续 Agent 必须先检查 PR #30 最新评论及本节，避免重复早期“组织余额/Jobs 权限不足”诊断。
- CLI 成功 Job：`https://huggingface.co/jobs/adradar/6af2ee90ab34849891ab2f6e`；ChatGPT 无 Volume Job：`https://huggingface.co/jobs/adradar/6af2ec43ab34849891ab279c`。

## 2026-11-10 补充证据：OAuth 授权确认页面截图（Owner 提供）

Owner 提供的 Hugging Face OAuth 授权页面截图显示：
- Repositories / Read repositories：读取用户可访问的私有及 gated repos。
- Repositories / Contribute to repositories：创建 repos 并管理由该 app 创建的 repos；页面明确注明 `Cannot access other repos`。
- Compute / Jobs：`Start Jobs on your behalf and read their status, logs and outputs`。
- Compute / Inference Providers：代表用户调用 Inference Providers。
- Account / MCP tools：读取 MCP tools。
- Organization grant 选择 `Grant ChatGPT the same access to selected organizations`，且 `Hong Kong Adradar Technology Limited` 已勾选（同时页面显示 Select all organizations 已勾选）。

### 对诊断的影响
该截图确认授权界面确实授予 Jobs 和指定组织访问，但没有单独列出 Bucket / Storage write permission。`Contribute to repositories` 的界面描述明确限定为 app-created repositories，不能据此推导它允许写入既有 `adradar/storyforge-training` Bucket。结合 ChatGPT RW Job 403 与 Mac CLI 同 Bucket RW 成功，最值得 HF 核查的是：Jobs OAuth 授权是否包含对既有组织 Bucket 的 RW mount / Xet write-token 签发能力，或该能力是否需要 OAuth App 额外 capability / grant。

此截图仍不能单独证明根因：页面未展示底层 OAuth scopes、Bucket-specific permission model 或 403 服务端拒绝码。不得把“缺少 Bucket write scope”写成已确认事实。应向 Hugging Face 提供 OAuth App ID `asdk_app_6ac752d4c640819191c206f9cb0dafad`、Plugin v0.1.4、此授权页面截图、Mac CLI Job `6af2ee90ab34849891ab2f6e` 和 ChatGPT RW 403 对照，请其确认 Jobs token 是否能签发既有 Bucket 的 Xet write token。

### Owner 授权范围说明
截图中组织授权范围为选定组织（当前截图同时勾选 Select all organizations 与 Hong Kong Adradar Technology Limited）。后续若重新授权，应只选择完成 StoryForge 工作所需的 `Hong Kong Adradar Technology Limited`，除非 Owner 明确希望授权其他组织；本截图不构成要求扩大组织授权范围的理由。

## 2026-11-10 主线续进：Worker CLI / Job bootstrap 工程实现

Owner 已暂停 ChatGPT-HF OAuth / Bucket RW 故障排查，并将自行在 Mac CLI 执行 HF 任务。ChatGPT 不再提交 HF Job、不测试 Bucket、不更改 OAuth；后续只提供可复用代码、命令、SAFE schema 与回执审查。

当前分支 `r60/p4-generation-eval-framework` 正在完成 P4 Worker CLI / Job execution plan 闭环：
- `worker.py` 保持模型无关的 generation batch engine，不导入 torch / transformers / HF Hub。
- 新增独立 `worker_cli.py`，作为真正的 `python -m storyforge_dataset.generation_eval.worker_cli` 执行入口；必须先通过 Profile freeze/inference/GPU 授权检查，再校验依赖 lock、runtime、manifest、input SHA、输出目录和私有输出权限；未授权时只输出 SAFE HOLD，不加载模型。
- Job plan 固定从 GitHub codeload 下载精确 `code_revision` 的仓库归档，限制归档大小/文件数/解压总量并拒绝路径穿越、符号链接和特殊文件；不依赖 PyTorch 基础镜像预装 git。
- Job 启动后按 `requirements/hf-generation-eval.lock` 使用 `--require-hashes` 安装依赖，再执行独立 Worker CLI；输入挂载路径为 `/input/generation-profile.json`、`/input/manifest.json`、`/input/inputs.jsonl`，输出目录必须为 `/output` 的全新直接子目录。
- Worker 仅将私有生成正文写入 `/output/<run-id>/<role>-outputs.private.json`，create-only、0600；stdout 只输出 SAFE 元数据，不输出生成正文。
- 当前提交 `219fd80f35d8b8e3c2da8a1b2d64a8dddeae008c` 的 Repository CI 与 R60 Generation Eval CI 已 PASS；Runtime Image Candidate 正在执行，尚未报告最终结果。

此代码目前仍是执行入口工程候选，不代表正式 Profile 已冻结或获准执行。未完成实际容器启动/归档下载的无 GPU 验证、运行镜像验证、Owner 本地 HF 端到端执行及 32K 资源预算复核前，不提交正式评估 Job。

### 后续主线顺序
1. 等待当前 HEAD 的 Runtime Image Candidate 真实回执；失败按日志修复，不沿用旧 SHA 的 CI 结果。
2. 增加 Worker CLI 归档 bootstrap 的语法/边界测试及 CPU-only container entrypoint test；确认镜像不依赖未安装的 git。
3. 由 Owner 在 Mac CLI 进行无 GPU/无私有数据的执行入口检查；如需 HF Job，由 Owner 决定并执行。ChatGPT 不代为提交。
4. 复核输出目录契约、SAFE 回收方式和私有正文保管；HF Bucket RW 问题暂时不在 ChatGPT 执行范围内。
5. 完成 32K 长上下文显存/时间/费用上限证据后，生成最终 Profile Freeze Review 包，等待 Owner 单独批准 Profile Freeze。Freeze 不自动授权正式推理。

### 不变的授权边界
`profile_freeze_authorized=false`、`inference_authorized=false`、`gpu_authorized=false`、`training_authorized=false`。不启动 Development20 / Locked30 正式推理、1000 条审核或 SFT；不读取 Locked30 私有案例。