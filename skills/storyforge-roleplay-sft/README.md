# R58 RolePlay→StoryForge SFT Skill v0.1.7

此目录是可移植的 **Skill 草案 + 已在合成数据上测试的离线工具**。它不会自动连接生产数据库、向 GitHub 写入、运行推理或启动付费 Hugging Face Job。需要安装到目标的 Skill 运行环境时，由 Owner 先检查 SKILL.md、SQL 和脚本；不要称其已安装或完成真实数据准入。

运行顺序（须在获授权的 Hugging Face 私有工作区运行脚本，**不要用 Mac/Docker 进行项目计算**）：

```bash
python scripts/r58_intake.py shortlist --input stories.csv --output selected_private.jsonl --limit 30
python scripts/r58_intake.py gate --input reviewed_private.jsonl --output decision_private.jsonl --safe-output decision_safe.json
python scripts/r58_intake.py freeze --input ready_private.jsonl --decision decision_private.jsonl --output-dir new-private-freeze-dir --world-graph-sha <SHA256>
```

`tests/` 只使用虚构数据，在沙箱环境可离线运行。R58 GPU 文学评审的逐字引用诊断与 Batch Quote Repair v2 批量候选索引纠错规则见 `docs/standards/R58_GPU_REVIEW_QUOTE_VALIDATION_CN.md`；模型一次返回所有无效位置的候选索引，程序校验位置集合并从允许来源提取精确原文；不允许模型改写引用，不放宽引用标准，也不会自动提交 GPU Job。

阶段差异：短名单无需正文；`gate` 需要外部完成的逐案证据，不替 Reviewer 判语义；`freeze` 仅冻结带完整已验证 System/历史的字节，不验证真实 runtime 本身。后续 HF CPU `collator` PASS 和 Owner GPU 授权属于额外门禁。

## HF CPU Token 预检与工具复用（v0.1.2）

每次 SFT、文学盲审或评估前，先执行 SKILL.md 中的“HF Token 预检复用”，并读取仓库唯一技术标准 [HF_TOKEN_PREFLIGHT_REUSE_CN.md](../../docs/standards/HF_TOKEN_PREFLIGHT_REUSE_CN.md)。优先使用 [共享 Token 核心](../../src/storyforge_dataset/token_preflight.py) 与既有真实 HF CPU SAFE 回执；不能每轮重新编写 Token 计数器。

- **Mac 不运行模型 Tokenizer**；仅进行私人数据分发、字节一致性与 SAFE 回执检查。真正计算在获授权的 HF CPU 环境完成。
- R58 Gold195 文学 13 条双审已经有 CPU 适配器与 GPU 评审器共用核心。已生成 PRIVATE STAGE 时，使用 `r58_hf_gpu_review_stage.py --refresh-code` 校验并仅更新代码，不能覆盖私人源数据和既有评审检查点。
- 缓存复用必须核对原始数据/Prompt/代码、模型不可变 revision、Tokenizer 与 Transformers、thinking、预算等全部身份；当前只实现完整 13 条批次复用，不承诺跨案例增量缓存。
- 预检失败只输出固定 SAFE 阶段码（输入、Tokenizer 加载、Chat Template 渲染、Token ID 解析），不输出原始异常、Prompt 或 Token ID；诊断码不改变 HOLD/PASS。
- 旧 `r58_intake.py gate/freeze` 的精确生产回放 G2 合同与 Quality-v1 新训练主线分离；不得伪造旧 G2 PASS 或直接把旧 Freeze 状态冒充数据准入。
- 用户明确要求 HF CPU Token 预检时，按范围提交最小必要 CPU Job，无需逐 Job 费用授权；GPU 推理/训练仍需单独明确授权。Token PASS 不代表中文文学质量、安全或训练准入。

技术实现与历史工具清单以仓库文档为准，Skill 保留执行规则，不复制工具源码或另建一套真相来源。

## v0.1.4 引用纠错

引用修复改为候选索引选择：模型只返回一个整数索引，程序从可见历史或目标回复的原文句段中提取引用；仅替换失败字段对应位置，评分与其他判断字段不经过修复模型。最多一次；失败仍 HOLD。

## v0.1.5 严重标记诊断

`RESPONSE_SEVERE_MUST_REJECT` 不能单独说明具体触发原因。新版 SAFE 只输出样本索引、decision 枚举值、触发的严重标记名称和数量；不输出原始模型响应或私人文本。旧回执缺少这些字段时不得猜测根因，应先增强诊断和合成测试，再决定是否重试未完成样本。

## v0.1.7 严重标记阈值与 Prompt 身份

严重玩家自主权只针对明确、实质性接管玩家关键行动/选择/台词/意愿/同意或拒绝；NPC 自身行动、心理、提问、改变话题或未等待回答不自动算越权。硬事实只依据可见历史明确规则，未认证卡片不能单独作为依据。checkpoint v2 绑定 `review_policy_version` 与 `prompt_sha256`；Prompt 变更后旧 checkpoint 不可复用，A/B 必须在同一 Prompt 版本下重新评估。

## v0.1.7 Batch Quote Repair v2

一次 repair call 批量修复 source/target 所有无效 quote 位置；模型只输出 field、quote_index、candidate_index。程序拒绝重复、遗漏、额外位置或逐字段候选越界。Checkpoint v3 的 Prompt SHA256 同时绑定纠错协议版本、模板、Schema 与上限；旧 v1/v2 checkpoint 不复用。
