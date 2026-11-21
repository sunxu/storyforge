# StoryForge R60 Base336 → Gold48 Quality-v1：新 Agent 唯一启动提示词（2026-11-22）

## 2026-11-22 最新 Owner 指示：不做无私有数据校准，直接进入正式 Judge

已有 Owner Mac 240/240 匿名包 create-only PASS，Gold48 Judge 配置只读 SAFE GOLD48_JUDGE_CONFIG_PREFLIGHT_PASS__NO_OUTPUT_NO_API 已 PASS。**不重复预检/匿名打包、不另跑无私有数据模型能力校准**。选用 J1 DeepSeek-V4.1-Flash / Fireworks AI 与 J2 GLM-5.2 / DeepInfra，使用现有配置、温度0、max_tokens 2048；先由 Owner 核对配置并运行 gold48_judge_lock --out **一次性冻结**，不可事后换评审者/权重或覆盖锁。该 Owner 真实锁状态仍等待 SAFE 回执。

为最短路径，已有 src/storyforge_gold_quality/gold48_judge_step.py 薄入口单条处理一个 reviewer_id×position，复用原 gold48_hf_judge.judge_one；请求前的 0600 create-only marker 禁止崩溃后自动重试，成功产生私有 0600 评分，空回复统一固定规则且无 API。不是新 GPU/通用 Runner/批处理架构，不允许自动循环重试。Owner 的第三方语料外发许可、HF 组织真实费用上限和计费批准尚未确认，不能仅凭“继续推进”或离线锁 SAFE 把 private_transfer_authorized 从 false 提升至 true；正式 API 仍为 0/$0，评分 0/240，quality_v1_admitted=0。

后续唯一执行入口与费用/隐私门禁见 Owner runbook 顶部。**未获准外发前仅完成本地合同冻结，不发送任何真实 Story/历史回答，不解盲。** 原下方“格式测试/模型校准/再做匿名包”属于旧建议，当前不得重复执行。

---

## 2026-11-22 实际盲评包 PASS；当前只做离线 Judge 合同，不再重复打包

Owner Mac 已实际返回 `GOLD48_240_BLIND_OBJECTS_PREPARED__NO_JUDGE_CALLS`：240/240 匿名回答已经**私有 create-only 创建**，48 主分析/42 敏感性，8 Story/25 Session，7 条 `length`、1 条无可见回复全部保留。无模型评分、无 HF API、$0、未外发、未解盲、`quality_v1_admitted=0`。之前的只读预检/打包命令**均已完成，不重做，不覆盖任何输出**。

现有分支新增 `src/storyforge_gold_quality/gold48_judge_lock.py` 和 `tests/test_gold48_judge_lock.py`：只读检查匿名包 240/48×5/1空回复、不同模型+Provider 的两评审配置，绑定整包 SHA 与 `gold48_hf_judge.py` 实际代码 SHA，create-only 写入 Owner 私有 0600 离线合同；锁内明确 `private_transfer_authorized=false`、`paid_calls_authorized=false`，不能开 HF、解盲或暗示获得人工独立性证据。代码只有锁，不是批量收费运行器或费用硬限制器。待 Owner 审定模型/Provider/结构化 JSON 能力/预算/独立复审流程及明确第三方外发授权后，才能进入受控的真实评分执行（预计两 Reviewer ×239 非空项 =478 次上限；空回复两项机械评分，非 AI Judge）。**下一唯一行动**：按 [Owner runbook 顶部](R60_GOLD48_OWNER_LOCAL_RUNBOOK_20261121_CN.md) 审核候选配置，并仅执行新模块 `--pack ... --config ...` 的只读、零 API 预检；Owner 接受并确认冻结配置后才追加 `--out`，无须修改生成器/输入/匿名包/Owner key。若模型与参数未批准，配置冻结仍 HOLD，禁止实际付费请求。

---

## 2026-11-22 真实 Owner 预检发现的唯一空回答：现行评分规则

Owner Mac 已只读核实 9/9 输入文件存在；初次 Gold48 盲评预检因 `EMPTY_GENERATION_HOLD` 停止。安全计数诊断定位 **192 个冻结生成记录中恰好 1 条无可见回复**（原始记录为 `text=""`、`finish_reason=eos`、`output_tokens=1`）；另外三个生成臂空回复 0。**Owner 原始回答/故事内容与来源映射不得写入公开 Git**。四臂各 48/48 及 SHA 已通过独立 Owner 字节审计，该真实空回答不能重新生成、替换、删除，48 主分析必须保留。

现有生成/字节审计容许空字符串，原新增 `gold48_blind.py` 却过度要求非空。仅修该数据约束以**原样保留** 240 个回答对象；新 SAFE `no_visible_reply_answers_retained` 汇总无回复数量。为避免在 HF Judge 强行制造候选原文引用，`gold48_hf_judge.py` 对无可见回复在已验证身份与固定调用参数/Owner 外发授权的前提下，按**明示的统一缺失回复规则**机械记六维 1 分、严重违规标记全 false、候选引文空，备注清楚“非 AI 模型评审”；**不向 API 发送此条私有上下文，也不计为实际 LLM Judge 调用**。其余非空回复保持原来的严格逐字引文和付费 API 评分合同。全部评分前须冻结并披露这项规则；不能把机械评分谎称独立模型评分。合成测试必须覆盖空输出保真、无伪造证据、无外发、无无授权绕过。

**真实 Owner SAFE 已 PASS（2026-11-22）**：`GOLD48_48X5_SOURCE_PREFLIGHT_PASS__NO_OUTPUT_NO_JUDGE`，48 题 × 5 来源 =240，8 Story /25 Session，48 主分析/42 敏感性，7 份 `length` 和 1 份空可见回复原样保留。未写盲评包，`api_calls=0`、`cost_usd=0`、`judge_scores_completed=0`、`quality_v1_admitted=0`；**不要再重跑预检**。现行唯一下一步：在 Owner Mac 按 [Owner runbook 顶部](R60_GOLD48_OWNER_LOCAL_RUNBOOK_20261121_CN.md) 用已验证九路径和现有 `gold48_blind --out` **一次性、create-only** 创建 240 份私有匿名包及单独 Owner key，签收 `GOLD48_240_BLIND_OBJECTS_PREPARED__NO_JUDGE_CALLS`。打包不等于允许外发或付费。下一关才是冻结六维/空回答规则、HF Judge 模型与 Provider/参数、独立评审/分歧规则、预算和 Owner 的实际第三方私有数据外发授权；此前保持 API 为零。

---

## 2026-11-22 Gold48 盲评薄适配已落地（优先于下方“适配待开发”描述）

- PR #31 **同一分支**已新增 `src/storyforge_gold_quality/gold48_blind.py`（48×5 只读数据契约预检、私有匿名打包、Owner-only 映射、0600/0700 create-only）与 `src/storyforge_gold_quality/gold48_hf_judge.py`（六维 1–5、严重标记、可定位引用、HF Inference Providers **单对象调用薄接口**及 `bill_to="adradar"`，默认拒绝真实外发）；合成用例见 `tests/test_gold48_blind.py`、`tests/test_gold48_hf_judge.py`。固定已有 R48/R55、Quality-v1 原代码不变，没有新增数据库、Runner、GPU 或评分批处理系统。
- **实况优先于历史 HEAD**：2026-11-22 Owner Mac 真实 `48×5` 只读预检已 PASS；代码 HEAD 以当前 GitHub PR #31 为准，合成 CI 只能证明软件合同，不能替代本次真实 Owner SAFE，也不能当作完成 Judge。
- 真正正式评分仍为 **0/240**，HF Providers API 调用 **0**、费用 **$0**、私有语料外发 **0**、评分冻结 **HOLD**、`quality_v1_admitted=0`、模型未晋升；既有 192/192 Owner 字节审计、48 Original 冻结与 7 个 length 继承不重做。Owner Mac 私有路径、原文、匿名映射均未被本次 GitHub 修改读取或上传。
- **唯一下一步**：不要重复已 PASS 的只读预检；按 Owner runbook 使用现有九路径与 `--out` 在 Owner 私有 `0700/0600` 域一次性产生匿名包和 coordinator key，保存 SAFE；在配置/权限/预算冻结前，不运行真实 Judge。
- 真实数据 PASS 后才可在 Owner 私有域选择并冻结独立 AI Judge 模型/Provider/参数/评审数量/分歧规则/预算、私有外发许可和计费额度；这些尚**未**冻结，**不能**把单次 HF 测试等同于正式 240 评分授权。正式评分原件全部齐备、不可变冻结后才能私有解盲；AI Judge 不等于独立人工评审。

---


> **直接复制本文件全文给新 Agent。** 这是当前阶段的任务与执行边界；2026-11-21 及更旧“等待 GPU / ready / 192 条生成”的内容只作历史。任务是**完成五来源六维盲评**，不是再做生成、训练或来源清点。

## 你是谁，目标是什么

你是 `sunxu/storyforge` 的 Gold48 Quality-v1 接手 Agent，继续 [PR #31](https://github.com/sunxu/storyforge/pull/31) 的现有分支 `docs/r60-p2-r47-r48-r55-source-shape-audit-20261118`，目标是用**最少代码与最短安全路径**完成已冻结 **48 题 × 五种匿名回答来源 = 240 份待评分回答**的独立六维评审、48/42 配对分析与 Owner 裁决。不要重新选样本、模型、输入、随机种子、原始回复或训练来源。阅读本文件与 [主任务书最新顶部](R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md)、[质量总计划最新顶部](plans/R60_BASE336_POST_TRAIN_QUALITY_EVALUATION_20261117_CN.md)、[Owner runbook 最新顶部](R60_GOLD48_OWNER_LOCAL_RUNBOOK_20261121_CN.md)、[AGENTS.md](../AGENTS.md)；以实时 HEAD 和真实 Owner SAFE 判断事实，不把文档写死的旧 HEAD 当最新。

## 已真实完成：继承，不得重复

| 生成臂 | Run ID | HF Job（COMPLETED） | Owner 字节审计 PASS | 停止原因 |
| --- | --- | --- | --- | --- |
| Base Qwen/Qwen3.8-27B | `gold48-owner-20261121T070218Z-6d825fa497b5` | `6b0147124fdc5ab3c55c7e00` | 4 文件、48 记录 | 47 eos / 1 length |
| R46 v0.2 checkpoint-7 | `gold48-owner-20261121T100447Z-1ea12fbfdf50` | `6b016f2befaf5e14f4b4db78` | 4 文件、48 记录 | 46 eos / 2 length |
| R54 v0.3-A checkpoint-16 | `gold48-owner-20261121T120421Z-4c3dbaf822d8` | `6b018ad1efaf5e14f4b52508` | 4 文件、48 记录 | 47 eos / 1 length |
| R60 Base336 checkpoint-37 | `gold48-owner-20261121T135310Z-bd614a15d46b` | `6b01a9c8efaf5e14f4b56b63` | 4 文件、48 记录 | 45 eos / 3 length |

**192/192 新模型回复已生成、交付与 Owner Mac 重新下载 SHA/结构审计通过；7 条 length 全部保留**。历史 Original Assistant Reply 48 份另经 Owner 冻结 SHA，**未传给 GPU 生成 Stage**；作为第五匿名来源只做同剧情**描述性**参考，不能声称与四新模型的重建输入 byte-exact 同题。8 Story/25 Session，主分析 48 题、已预注册剔除风险 Story 的整组六题后 42 题敏感性；实际六题映射需复用并核对 Owner 私有证据，不能凭 `Pxx`/`Sxx` 猜。最后核验 PR HEAD `4caf2e3dd5a7d6b2575b2cac0e2c1e0a86a02f40`、7/7 GitHub Actions SUCCESS（**接手先重新核对实时 HEAD/CI**）。

**严格事实边界**：Owner SAFE 的 `owner_mac_job_image_inspect_verified=false`、`owner_signature_independently_reverified=false`、`provider_signature_independently_reverified=false` 仍然为 false。HF Inspect 中配置的镜像 Digest 不是独立镜像证明，不需要重跑生成补签名；`quality_v1_admitted=0`、盲评未开始、`model_promoted=false`。本轮已批准的 `RECONSTRUCTED_EVALUATION_INPUT` 不是历史 Provider actual-sent 字节；全历史来源独立性不是已证全宇宙 PASS。

## 只做以下最短剩余工作

1. **核对现有私有原件，不重新提取**：Owner Mac 已有 `~/.local/share/storyforge/r60/private/gold48-owner-results/<run_id>/` 四臂私有结果（每臂四文件）、既存 48 冻结重建输入、48 历史 Original 与真实 Story/Session/风险来源私有 crosswalk。先只读核对 48×4 +48=240 个必要数据对象、同题输入和已签收 SHA、48/42 标记；只输出 SAFE 汇总。文件具体位置从现有 Owner manifest/回执读取，不猜造。若一个必要私有绑定缺失，明确 HOLD 单项并保持已签收产物不变。
2. **先复用再补薄适配**：阅读 `scripts/v02_r48_four_arm_build.py`、`scripts/v02_r48_review_aggregate.py`、`docs/V02_R48_FOUR_ARM_BLIND_REVIEWER_GUIDE.md` 及 `docs/evidence/V03_R55_GOLD5_REAL_ALIGNMENT_OWNER_RECEIPT_AND_V2_BLIND_FIX_20261023.md`。原 R48 固定 20 题 ×4 来源×3 独立评审者，**不可直接把其 CLI 用在 48×5**，仅复用六维指标、匿名随机化、评分输入不变性、严重标记、原件冻结和解盲前 SHA 校验原则。先查现有 `src/storyforge_gold_quality/` 与相关质量代码确切能力，只有明确缺口才新建最小数据/API 适配；用 stdlib/现有测试做无私有数据的合成测试。保持私有 `0700/0600`、create-only，分离匿名回答包与 coordinator-only 来源映射。
3. **固定 AI 盲审合同，再做任何正式计费调用**：Owner 已实际成功测试 **HF Inference Providers API + `adradar` 组织计费**，此选型已定，不要再讨论替代平台或自建 GPU Judge。通过现有 `huggingface_hub.InferenceClient` 的 `bill_to="adradar"`（或等价组织头），固定实际可用的评审模型/提供商/温度/输出 token 限额/六维 rubric/1–5 整数 +依据/严重标记结构、独立评审数与分歧解决方案、并发重试及预算上限；遵守 Owner 私有聊天向实际第三方 Provider 发送的授权/隐私限制。**LLM-as-judge ≠ 人类独立 Reviewer**，不得虚称人工或自动推断“已独立”。仅先做不含私有语料的格式试验；正式评估前冻结匿名包 SHA 与 Judge 配置，以免看答案后换 Judge/权重。HF 推理细粒度 `HF_TOKEN` 曾覆盖 Mac Bucket 凭据引发 `BucketNotFoundError`；API/私有 Bucket 分隔环境与权限，Token 不写入 Git、Bucket、日志和聊天。
4. **盲化且严禁泄露来源**：同一题五回答随机化，以中性标签送评分器，隐藏 Base/R46/R54/R60/历史 Original 与交叉映射，尤其不能让评分器先识别 Original 再给“四模型最优”（R55 v1 缺陷）。若预注册需要四模型专属最佳，**独立**生成无 Original 的四方匿名任务；不能从五来源评分中反推模型身份。逐回答六维固定为剧情连续性、角色一致性、指令遵循、文学表现力、互动推进、玩家自主权（1–5 整数），并保留原文依据、严重违约/玩家自主权侵犯标记和独立评审差异。七条 `length` 仍参与主分析，同时可按预注册规则提供 completed-only 补充敏感性分析，不篡改主集合。
5. **评分冻结 → Owner 私有解盲 → 分析**：确保评审所有预设对象/格、题序、原文、证据、成本/失败记录和评审模型身份一致，create-only 保存实际评分及 SHA。**必须在所有必要独立评分真实完成并冻结后才由 coordinator 打开私有 answer key**。主分析 48 题，风险 Story 整组六题剔除的 42 题敏感性；按 8 Story/25 Session 统计相关性。重点比较 R60 vs Base、R60 vs R46；R54 用作诊断；Original 保持描述性第五参考。报告六维、严重标记、效果大小/不确定性、`length` 与来源风险、未测 actual-sent/保护全集范围，最终由 Owner 裁决，不能自动晋升模型。

## 禁止事项与边界

- **禁止重跑 Base/R46/R54/R60、Tokenizer CPU、Adapter 1.87GB 哈希、旧 R50/R47/R48/R55/R58 审计、204 Story/495 版本复审、48 输入/历史 Original 恢复、Git 冻结 Profile 改动**。
- 禁止在 Mac 安装 `torch`/`transformers`/`peft`、重新训练/提交新 GPU、增设 Supabase/PostgreSQL/通用 Runner、重写已存在的 Quality-v1 功能或复制旧 R48 系统。
- 不读取 R50 sealed、未授权生产聊天；不公开私有 Story/角色/Session、Prompt、原始回复、逐案哈希、Reviewer 评分原文、crosswalk、HF Token；不将私有输入/答卷发布公开 Dataset。
- 失败只定位且修复唯一缺口，不偷偷跳过校验或重试造成重复费用；一次性任务和敏感文件不能覆盖。没有 Owner 允许的外发范围或无法确定 Provider 数据处理条件时，只能先完成本地匿名包/合成测试，不发送真实私有材料。
- **只在确有阻塞缺口时做最小代码与合成测试变更，继续 PR #31 同一分支**；变更后检查 HEAD/CI。不要请求用户重复已提供的 Owner SAFE 和四臂审计。

## 立即执行顺序与交付

**第一轮直接做（不要停留在空泛方案）**：查看 PR #31 实时 HEAD/CI、现有 R48/R55/Quality-v1 代码和 Owner 私有资产是否已暴露可读的现有 SAFE/清单；列出**已复用能力、真实缺口**。在不接触真实私有内容的情况下，准备最小 48×5 匿名数据契约 + HF API Judge 输出契约的合成验证。仅在必要时提出针对 Owner Mac **一条**只读 SAFE 盘点命令；不要要求上传历史明文或重复 SHA 审计。确定后沿最短路径实施缺口（若需要写代码，先核验 CI，禁止无关重构）。

每次汇报：PR/HEAD/CI、真实通过/真实 HOLD、Owner 私有数据/外发是否发生、HF Job/API 调用与费用、模型评分数量、`quality_v1_admitted`/模型晋升状态、**唯一下一步**。未执行的动作绝不报 PASS。
