# StoryForge R60 P4：正式三模型配对评测准备任务书 v1（CPU-only）

## 2026-11-10 主线纠偏（优先于下文全部规划）

**唯一当前业务目标：用已冻结的 Rubric v2.1 和 Gold/Owner 裁决校准 A（Qwen3-32B）、B（GLM-4-32B-0414）、challenger（GLM-Z1-32B-0414）作为历史训练数据质量审核模型/审核组合，进而精筛 Supabase 粗筛的约 1000 条候选，形成符合 Quality-v1 的可训练数据，随后另行授权 StoryForge SFT。**

**优先级 P0 = 下文「评测线 S」的 30 条严格配对三模型盲审和 P5 审核准确性分析。** 三维 Hard Rule、Player Agency、Safety 是 R60 严重问题校准主轴；模型输出须符合冻结的裁决 schema，而不是故事续写。先精确验证 Owner reference 与三模型新预测的隔离，再冻结预测、按维度计算漏判/误判/弃判、分析分歧。不可凭任何一个模型输出长度决定模型审核能力或把三模型“写故事能力”作为本阶段选型依据。

**下文「评测线 W」仅作为未来可选的故事生成研究草案，目前 DEFERRED，不在本轮 P4/P5 的执行范围，不做 W-pilot、W-12 样本准备、GPU 推理、文学盲评或训练模型排名。** 原先叙述“两条评测线同时准备”属于偏离 R60 主线，不得据此安排执行。前期新建的 `formal_pairing_gate.py` 是 CPU-only 的 JSONL 严格配对结构校验助手，**不是** Rubric 三维预测 Verifier，也不代表 P4 30 条评测授权或正式数据检查 PASS。

**当前下一步**：核对 P2-B 已冻结的 30 个 blind case 及 private reference 隔离可达性、固定 exact 30×3 预测输入和 SHA、补齐结构化三维裁决模型输出及 verifier、CPU-only 生成不提交的三模型推理计划和资源预算；三模型合成 GPU 子阶段已 PASS，无需重跑。formal inference 仅原则授权，`execution_activated=false`，Owner Mac CLI 执行之前仍需独立执行门槛。1000 条批量审核与 SFT 均未授权。

---


> 2026-11-10。**当前状态：FORMAL_EVAL_PREPARATION_IN_PROGRESS__NO_GPU_JOB**。本文件只确定下一阶段架构、输入门槛与验收标准；未对真实私有样本执行抽取、Token 预检或任何推理。所有历史已冻结裁决原样保留。

## 一、已完成的工程依据

三个固定 revision 的模型均在 Owner Mac 提交的真实 H200 单次合成 Job 完成接近 32K 输入推理与私有输出 SHA 回读：

| 角色/模型 | Job ID | 输入 tokens | 输出 tokens | EOS/截断 |
|---|---|---:|---:|---|
| A / Qwen/Qwen3-32B | `6af32a97ab34849891ac0461` | 28568 | 312 | EOS/0 |
| B / zai-org/GLM-4-32B-0414 | `6af32e14ab34849891ac0d16` | 28593 | 7 | EOS/0 |
| challenger / zai-org/GLM-Z1-32B-0414 | `6af3316f9737d9a9e090c0e4` | 28597 | 378 | EOS/0 |

三者都证明 **GPU 环境、模型加载、长输入生成、文件存储和读取链路可用**。但合成提示的最后要求是「请输出一句简短中文确认」，所以 **7 tokens 并不自动构成故障**；A/GLM-Z1 生成更长也不意味着故事质量更好。三个模型的 sampling、thinking 和 generation prefix 不相同；原始短回复长度不具有公平的质量可比性。都没有验证持续解码满 4096 tokens。

合成阶段最终状态：`R60_P4_SYNTHETIC_32K_THREE_MODEL_GPU_AND_READBACK_PASS`。

## 二、正式比较必须回答两个不同问题

### 评测线 S：R60 严重问题判定（原定 P4/P5）

目标：检验三模型对原 Rubric v2.1 中 Hard Rule、Player Agency 和 Safety 三个严重维度的裁决能力。保持 P2-B 的 Locked Regression20 + Severe10 共 30 条、30×3 配对预测；**三个模型在同一条输入上的判断才可互相比较**，预测必须不含 Owner reference labels/旧答案/ID Map。

- 使用已有冻结的 Rubric v2.1、evaluation prompt SHA `51465853db6a2b61a9f87b1e9d5f23f7f02bd2c98b5a0d6a8ab2ec61322346e1`、output schema SHA `e6371bf3319affcae190b6ccb9a1b8ce778bae440a91eefe39a65b2586930d70`，不静默修改标准。
- P2-B 30/90 Owner 结果已验证，但存在明确的 `INSUFFICIENT_CONTEXT` 与 HOLD；这些不能被当作明确正确/错误的硬标签，也不能无条件计算进准确率分母。
- 冻结三模型预测后才允许用 Owner reference 评分。指标至少包括：每维可评分数、明确错误数、漏判、误判、弃判/HOLD、宏平均（且给出分母）；不可只给一个准确率。
- 30 条是严重问题判定集，**不是故事续写文采的默认金标准**；绝不根据 S 的得分直接宣称 StoryForge 写作最佳模型。

### 评测线 W：互动故事续写质量（另行固定样本）

目标：检验模型是否适合 StoryForge 的**实际输出任务**，包括世界与人物一致性、中文文学表达、NPC 剧情推进、玩家自主权、指令遵循、回复有效长度。

- 优先复用已经允许用于 development 的优质历史对话，在 Owner Mac 将真实的系统设定、历史消息、末轮玩家输入组装成可追溯 `messages`，不包含参考下一句或任何历史助手目标回复。
- 建议先选 **6 条开发集技术/格式 pilot**，要求故事、上下文长度、剧情位置尽量多样；pilot 只排查格式、EOS、空回复、速度与显存，不参加最终排名。
- 随后独立冻结 **至少 12 条跨故事质量对照样本**（具体数量和来源由可用数据证明，不得虚构已具备 12 条）；不能使用训练中的样本作为未见过的 held-out 质量证据。要求至少 4 个故事、含长中短上下文，若实际可用量不足则 HOLD。
- 三模型针对同一 case 必须有同一语义场景、相同轮次和玩家输入；各自通过固定 Chat Template tokenized，并对各模型分别检查真实 token 数与 28672 上限；绝不通过自动截断制造虚假公平。
- 明确测量可见故事文字与思考文字（thinking）区别：记录 decode tokens / 可见正文长度 / 空回复 / 格式异常 / EOS / length 截断。Qwen Thinking=True、GLM-4 template_default、GLM-Z1 generation prefix `<think>` 的**输出 token 总数包含 reasoning**，原始 token 数不等于可见故事正文篇幅。
- 盲评去掉模型名称、随机化 A/B/C 顺序；先独立按五维规则评分，再按 case 作成对比较；记录 reviewer 一致性及分歧，不允许读取训练答案、旧模型裁决后反过来改 prompt 或样本。
- 衡量标准分别报告：硬规则/玩家自主权违规率、设定一致性、中文质量、剧情推进、服从指令、有效回复长度，以及吞吐/成本。**以违反严重约束为优先 veto，不能让文采分数掩盖严重违规**。

## 三、共同输入、隔离与核验合同

正式数据须保持 Owner Mac 私有；GitHub 仅接收代码、schema、空模板、哈希和汇总 SAFE，不能提交故事正文、Owner reference labels、blind ID 映射、凭据或私有生成内容。

任何评测线的正式 GPU Job 启动之前，都要有独立固定的私有 case manifest 和相应 SAFE：

1. **范围门槛**：`track`（S/W）、`case_count`、`unique_case_count`、`stories_count`、冻结 case-set 哈希、`source_pool`、排除集核验、是否用于训练的检测结果。S 必须恰好 30 个 P2-B case 且有 P2-B frozen manifest 绑定；W 不得假定已有未使用故事。
2. **三模型同案配对**：同一批不可逆内部 case ID 在 A/B/challenger 中一一对应、顺序可以不同但有私有 crosswalk；每个角色的独立 JSONL SHA256、记录数、token 范围（不超过 28672）、真实 tokenizer/template fingerprint 均验证。不能仅凭每个模型都有 30 条就称严格配对。
3. **推理合同**：固定各模型 revision/tokenizer/template、共同的评价 prompt/schema SHA、选定 sampling、seed、EOS、pad、reasoning 与 decode 指标。评测线 S 的预测 schema 不得直接复用故事文本生成 schema 而无解析/验证。
4. **安全隔离**：模型输入不含 Owner reference label、旧预测、训练答案、ID Map；技术人员生成预测时不能读到 blind reference；输出持久存储 create-only、0600，读回必须 SHA 一致；仅 Owner 在预测冻结后做私有 crosswalk 对齐。
5. **资源控制**：每次 Job 限定一个模型，Owner Mac CLI 亲自提交，不自动重试；正式测试单次 batch 数、GPU flavor、预估 tokens/s、运行分钟和预算**尚未实测/未冻结**，不得照搬合成单 case 60m/$5 估计为 30 case 成本。
6. **正式授权**：`p4_generation_execution_authorization_20261110.json` 仅声明 formal inference 原则授权，`execution_activated=false`，`no_automatic_submission=true`；冻结上述证据并验收后，须形成正式执行包和 Owner 审核记录，不能使用 synthetic-only 的授权开关处理真实内容。

## 四、当前代码差距（本次核实）

- `owner_h200_prepare.py` 是只接受三组精确 SHA 的合成脚本生成器；**不能**使用它提交真实数据。
- `synthetic_gate.authorize_synthetic_profile` 明确校验人工重复文本、固定 record_count=1，不能绕过、复制或改名使用在真实样本上。
- `worker_cli` 无 `--synthetic-authorization` 时要求正式 profile 自带 `inference_authorized=true` 和 `gpu_authorized=true`；Frozen JSON 仍为 false。**不得直接改写原 Frozen 文件**。
- `plan.build_generation_plan` 虽可生成不自动执行的 Job argv，但当前只接受正式 profile 的授权状态，且格式和评测线 S 的输出 schema / 严格配对约束尚未建立。
- `run_generation_batch` 的私有生成输出是 `outputs[].text` 等自由文本，没有完成 Rubric v2.1 三维结构化模型裁决及硬校验。不能把任意生成文字直接视作 P2-B 30/90 评测结果。

## 五、下一步 CPU-only 任务及完成条件

**F1：证据与来源盘点（优先）**。定位已有 P2-B frozen 30 input-only 资料的 Owner 可读位置，盘点 development 可用真实故事样本；只核对数量、角色/来源绑定、哈希、是否能够脱离 reference labels 生成消息；输出 SAFE。无法确认来源及隔离则 HOLD，不编造私有路径。

**F2：分轨输入合同与 Verifier**。实现不读取正文的 SAFE 清单、30 条严格配对 ID/哈希核对与 holdout 隔离；另为 W 编制盲评 rubric、样本挑选 schema。使用假数据覆盖配对缺失/重复、label 泄露、超预算、混用训练集等拒绝场景。

**F3：模型格式与短回复诊断**。CPU-only 对三模型冻结 template / EOS / generation prefix 作证据核验，记录哪些 token 属于 reasoning；特别检查 B 的 `output_tokens=7` 是符合合成 prompt 的一句话，还是可能有模板/停止符异常。目前仅有 EOS 计数，不能推断病因，也不需要自动重新做 GPU。

**F4：正式执行包 / 独立执行门槛**。F1–F3 通过后固定每 track 的 case count/sha/role inputs、GPU 预算和唯一 Job argv，另生成 Owner SAFE 许可记录。仅当 owner formally activates execution 才能在 Mac 运行；ChatGPT 不提交 HF Job。

## 六、状态

- `P4_SYNTHETIC_32K`：**PASS / CLOSED**。
- `P4_FORMAL_CPU_PREPARATION`：**IN PROGRESS**，本文件只完成设计及代码缺口核对，未声称数据源已验证。
- `P4_FORMAL_INPUT_MANIFEST`：**HOLD**（尚无 Owner SAFE）。
- `P4_FORMAL_GPU_EXECUTION`：**NOT ACTIVATED / NO JOB**。
- `P5_MODEL_SELECTION`：**NOT STARTED**。
- `P6_1000_BULK_REVIEW` 和 `SFT_TRAINING`：**NOT AUTHORIZED**。
