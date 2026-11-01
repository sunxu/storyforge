# StoryForge 可复用 HF Token Preflight 工具链

更新：2026-11-01。规范状态：**共享纯 Python 核心 + R58 CPU/GPU 适配器已落地；历史冻结实现不重写**。

## 一、统一核心（权威实现）

- 源代码：src/storyforge_dataset/token_preflight.py
- HF Job 可移植副本：PRIVATE input 目录中的 token_core.py（必须与源文件字节一致）
- 纯标准库、无 Hugging Face 调用、无 GPU、无模型权重加载
- 公共函数：extract_input_ids、encode_chat、describe_token_lengths、digest_serialized_items
- BatchEncoding 必须解析 input_ids，不能把 len(BatchEncoding) 的字段数量误认为 Token 数。
- 长提示词不允许少量假 Token 结果；输入输出预算按 `prompt_tokens + reserved_output_tokens <= max_model_len` 检查。
- 硬性禁止静默截断、丢弃历史、修改 Gold 或把 Token PASS 当成模型质量准入。

## 二、数据类型适配器

| 实验类别 | 已有适配器/检查工具 | 与统一核心的关系 |
| --- | --- | --- |
| R58 文学盲审 A/B 各 13 条 | experiments/r58_quality/r58_hf_cpu_literary_token_preflight.py + r58_hf_gpu_literary_reviewer.py | **已改为共享同一核心**，复用真实 GPU prompt_messages |
| R58 较早的 132 条语义审核 | gold195_hf_review_cpu_worker.py 与 hf_cpu132.sh | 历史已验证流程，保留冻结结果；后续新实验优先用共享核心 |
| R50 46 条 Held-out | scripts/v03_r50_hf_cpu46_audit.py | 原始来源与版本要求独立；不改动冻结记录 |
| R53 40 条真实 ms-swift | scripts/v03_r53_hf_cpu40_audit.py / worker.sh | 训练标签、ms-swift collator 不能只用文本 Tokenizer 代替 |
| SFT 基础配置/数据门禁 | scripts/hf_cpu_preflight.py | 结构与配置校验，不是模型 Token 统计 |

**新实验先写薄适配器，只负责数据格式、权限和本项目的 prompt serializer。禁止另造 Token 提取、p95、上下文预算的独立实现。** 一旦新适配器成熟，再合并同类入口；不为追求代码复用破坏冻结样本或审计证据。

## 三、SAFE 回执与避免重复付费

R58 HF CPU 私有回执（v2）记录：

- 输入文件原始字节 SHA256（PRIVATE）
- 实际批次序列化 prompt SHA256（PRIVATE，顺序敏感）
- 评审器代码 SHA256 与共享核心 SHA256
- 模型 ID + 不可变 SHA、Transformers 版本、Tokenizer 类、Chat Template SHA256
- thinking 参数由评审器与模型绑定；上下文上限、预留输出 Tokens
- 完整 13 条 min/median/p95/max、pilot2/rest11、超限数
- no GPU/no training/no quality admission

在 Mac **只做现有回执的完整性复核**（纯标准库，无 Tokenizer）：`r58_hf_cpu_literary_token_preflight.py --verify-cache-only`，参数与当初 HF CPU 预检一致。回执必须从先前可信 HF Job 的 PRIVATE RW 输出经 sync-back 回收，且所有身份参数完全匹配，才能复用为缓存 PASS；否则 HOLD。不得靠修改 SAFE JSON 伪造 PASS。不同输入或模板必须重新在 HF CPU 编码，并尽可能仅计算受影响条目。当前适配器按 13 条固定批次实现；跨案例增量缓存属后续优化，不得谎称已经完成。

**重要：缓存校验可以在 Mac 进行，但真正 Tokenizer 预检只能在 Hugging Face CPU 运行。** 读写私人故事只在个人 PRIVATE 目录与 HF PRIVATE volume，绝不上 GitHub Actions。

## 四、私人 STAGE 的代码升级

现有 RUN_DIR 为 r58-quality-pilot13-20261101T111719Z，现有 STAGE 为 r58-hf-gpu-dual-review-stage-20261101T114557Z。

Mac 获取最新代码后运行：

    python3 experiments/r58_quality/r58_hf_gpu_review_stage.py \
      --pilot-dir "$RUN_DIR" --stage-dir "$STAGE" --repo-root "$PWD" \
      --refresh-code

该命令对比每个 staging source.private.jsonl 与原盲审包字节，验证 Owner crosswalk 仅留在 Mac，不复制给 HF；只升级或补齐 runner.py、token_core.py、token_preflight.py，不改动任何原始数据及 output_A/B。若已经出现真实 GPU 评审检查点，直接 HOLD，禁止更换模型评审器代码后继续复用旧 checkpoint。命令重复执行应返回 code_files_updated=0（幂等）。

### 统一执行入口（先更新 GitHub，再在 Mac 执行）

提交 `9a65db38` 之后，仓库新增薄编排入口 `experiments/r58_quality/r58_refresh_existing_private_stage.sh`。它调用既有的 `r58_hf_gpu_review_stage.py --refresh-code`，**不复制 Token 核心，也不更改真实 Tokenizer 只能在 HF CPU 执行的规定**。

在 Mac 的 StoryForge 仓库工作树执行：

```bash
git switch r58/roleplay-sft-skill-v01
git pull --ff-only origin r58/roleplay-sft-skill-v01
bash experiments/r58_quality/r58_refresh_existing_private_stage.sh --refresh-and-test
```

入口默认使用本文第四节现有的私人 RUN_DIR/STAGE 路径；可通过 `R58_RUN_DIR` 和 `R58_STAGE` 环境变量覆盖。执行前必须处于正确分支、包含基线提交 `9a65db38`、且 Git 工作树干净。刷新前后校验私人输入、Owner crosswalk 和既有 output 的字节一致性；连续刷新两次，第二次更新数必须为 0。若发现真实 GPU reviewer checkpoint，沿用原工具的拒绝覆盖逻辑。

只运行不碰私人数据的合成测试：

```bash
bash experiments/r58_quality/r58_refresh_existing_private_stage.sh --synthetic-only
```

三组测试涵盖共享核心、R58 HF CPU/GPU 适配器和 Skill 合约。该脚本不会提交 HF Job，不下载模型 Tokenizer，不启动 GPU，不产生 Token PASS 或训练准入；真实 HF CPU Token 预检仅在用户明确要求执行该工作流时提交最小必要 CPU Job，不需要逐 Job 费用授权。

### R58 A/B 私有 Token 回执只读盘点

在已完成 STAGE 代码刷新与合成测试之后，使用现有统一入口：

```bash
git switch r58/roleplay-sft-skill-v01
git pull --ff-only origin r58/roleplay-sft-skill-v01
bash experiments/r58_quality/r58_refresh_existing_private_stage.sh --cache-inventory
```

此命令只访问此前 `STAGE/input_A,B/source.private.jsonl` 和 `STAGE/output_A,B/r58_cpu_preflight_all13_safe.json`，默认 STAGE 与第四节一致，必要时以 `R58_STAGE` 环境变量覆盖；**不运行模型 Tokenizer、不启动 HF Job、不重写私人文件**。内部复用 `r58_hf_cpu_literary_token_preflight.py::verify_reuse`；分别输出以下安全状态：

- `MISSING`：本地未找到该 slot 的回执，不等于 Token 失败。
- `LOCAL_MATCH_ORIGIN_UNVERIFIED`：本地输入、序列化 Prompt、代码 SHA，以及**独立提供的**模型 revision、Transformers 版本和评审预算与回执匹配；但**不能由本地回执自证来源于真实 HF CPU Job、或等价于未来 GPU runtime**，仍不可当作正式 GPU 准入。
- `HOLD`：路径/权限、回执格式或身份不匹配；不改写证据，不自动复算。命令退出码 42。

2026-11-01 修正：测试发现旧盘点器错误地将回执里的预算值当成校验的期望值（2400 改成 2401 也可能误判本地匹配）。`v2` 改为**fail-closed**：对已有回执，必须另行提供已批准/已记录的各槽位不可变模型 revision 与 Transformers 版本，预算按真实 GPU 评审器的既定默认值 32768/2400（如经明确审批改变，则通过独立 CLI 参数传入），绝不能从正在检查的回执中推断期望值。未提供独立 pin 时，若回执存在则 `HOLD`；如果回执不存在仍返回 `MISSING`。

已有回执并且已从**独立的评审配置记录**确定参数后，才能运行如下示例（尖括号仅是占位说明，执行时替换为真实 SHA 与版本，不要把示例值当成生产 pin）：

```bash
bash experiments/r58_quality/r58_refresh_existing_private_stage.sh --cache-inventory \\
  --expected-revision-a "$REV_A_40_HEX" \\
  --expected-revision-b "$REV_B_40_HEX" \\
  --expected-transformers-a "$TRANSFORMERS_A" \\
  --expected-transformers-b "$TRANSFORMERS_B"
```

以上 CLI 期望值仍须对应已确定的 GPU 目标配置，不能取自待核验的 SAFE JSON。可信 HF Job/PRIVATE sync-back 来源及未来 GPU runtime 等价性仍需单独核实。盘点脚本本身始终只读、绝不提交 Job；若用户明确要求真实 CPU 预检，则可提交所需的最小 HF CPU Job，无需额外逐 Job 费用授权。GPU 推理/训练仍需单独明确授权。该盘点脚本为薄适配器，底层 Token 提取与统计只有一份共享实现。

### CPU 预检失败诊断码（2026-11-01）

CPU 预检只输出固定 SAFE 诊断码，不打印 Python 异常文本、文件内容、Prompt、token ID 或私人路径：

- `PRIVATE_INPUT_SOURCE_*` / `PRIVATE_INPUT_JSON_INVALID`：输入 JSONL 或盲审契约校验失败。
- `TOKENIZER_IMPORT_FAILED`：Transformers/Tokenizer 依赖导入失败。
- `TOKENIZER_LOAD_FAILED`：指定模型 revision 的 Tokenizer 初始化/下载失败。
- `CHAT_TEMPLATE_MISSING`：Tokenizer 没有可用 chat template。
- `TOKENIZATION_FAILED`：Chat Template 编码失败。
- `TOKEN_BUDGET_SUMMARY_FAILED` / `PREFLIGHT_FINGERPRINT_FAILED`：统计或身份指纹步骤失败。

这些码只用于定位阶段，不会使 HOLD 自动转为 PASS。未知异常仍使用通用 `TOKENIZER_OR_PRIVATE_INPUT_ERROR`，绝不把异常消息原文输出到 Job 日志。诊断后应修复已识别原因，保留输入与预算不变，再运行同一共享预检核心。

## 五、下次使用前的最小决策

先问：已有有效 SAFE 回执吗？对比原始输入、真实 prompt、模型 revision、Tokenizer/运行时版本、thinking、预算和核心代码。如果全一致，无须支付另一笔 HF CPU Job；若任何关键事实改变，先复算必要范围，不能仅因为脚本换了名字或换了机器就重跑。

下次增加实验时优先扩展统一接口和自动缓存，而不是复制 R50/R53/R58 脚本。稳定共享核心应配合 synth 测试、失效缓存测试、Job 回收测试和冻结旧实现的兼容说明。

## 六、未完成事项

- 当前新共享路径的最新 GitHub CI 结果需确认（不能用旧成功 CI 冒充）。
- HF CPU A/B 全 13 条真实预检尚未执行，也未收到真实 SAFE 结果。
- GPU Docker 的 Transformers/chat-template 与 HF CPU 的等价性尚未实际验证。
- 更一般的跨案例增量缓存尚未实现；当前严格复用同一批次的可信回执。
- 本轮没有新 HF CPU/GPU 付费 Job，也没有训练授权。
