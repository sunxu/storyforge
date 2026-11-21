# StoryForge R60 Base336 → Gold48 Quality-v1：新 Agent 唯一启动提示词（2026-11-22）

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
