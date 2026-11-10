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