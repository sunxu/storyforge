# R60 Base336 训练后质量评估与 Skill 维护计划（2026-11-17）

## 1. 当前结论

**工程训练完成；独立质量评估未开始。**

- Owner 分支：`r60/common2-cpu2-owner`。
- 训练 Stage 绑定的源码 HEAD：`87bd0680c9f7321da12c70c490e2a6ebb875d503`。
- Run Key：`r60-base336-gpu-20261117T055622Z-b609cb78661d`。
- Hugging Face Job：[`6afbfd5c98dda891b5df7fd2`](https://huggingface.co/jobs/adradar/6afbfd5c98dda891b5df7fd2)，Owner 查询状态为 `COMPLETED`。
- 唯一提交回执确认 `job_submission_calls=1`、`hf_jobs_submitted=1`；没有自动重试。
- Worker SAFE：`BASE336_GPU_EXPLORATORY_ENGINEERING_PASS__NOT_PROMOTED`。
- Train / Validation：293 / 43；37/37 Optimizer Steps；1 Epoch。
- `terminal_checkpoint_verified=true`、`adapter_reload_verified=true`、`model_promoted=false`。
- `train_admitted=0`、`quality_v1_admitted=0`、`r50_read=false`。

Worker SAFE 中的 `hf_jobs_submitted=0` 是 Worker 不提交嵌套 HF Job 的固定字段；它不否定外层提交回执所记录的唯一训练 Job。

## 2. 训练证据摘要

| 项目 | 已核验值 |
|---|---:|
| GPU | NVIDIA A100-SXM4-80GB |
| GPU 总显存 | 79.2 GiB |
| 启动可用显存 | 78.8 GiB |
| 峰值显存 | 36,115 MiB |
| 模型 | Qwen/Qwen3.8-27B |
| 固定 Revision | `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` |
| LoRA rank / alpha | 64 / 128 |
| Optimizer Steps | 37 |
| Train Loss（Trainer 汇总） | 2.146966 |
| Terminal Eval Loss | 1.932103 |
| Terminal Eval Token Accuracy | 55.09% |
| Swift train runtime | 1,699.8 秒（约 28分20秒） |
| Worker 总耗时 | 1,948.8 秒（约 32分29秒） |

固定依赖：ms-swift 4.5.3、transformers 5.16.1、bitsandbytes 0.50.2、qwen-vl-utils 0.0.14、huggingface_hub 1.33.0。

训练评估日志的最终记录为 step 37/37，eval_loss=1.932103395；Trainer 汇总 train_loss=2.146966。它们是训练/验证损失指标，不是文学质量结论，也不能单独证明相对 Base 有提升。

## 3. HF 产物只读盘点与完整性边界

Owner 已对独立输出前缀完成递归文件盘点：

- 33 个远端对象，总计 5,604,774,224 bytes。
- 最终 `adapter_model.safetensors`：1,867,797,544 bytes。
- `checkpoint-37/optimizer.pt`：3,736,129,330 bytes。
- Worker SAFE、运行日志、reload 输入/输出、Trainer state、adapter config、训练日志、图表和 TensorBoard 事件均存在。
- HF Job 状态为 COMPLETED；最终 checkpoint、terminal eval、one epoch 和 adapter reload 均由 Worker SAFE 确认。

**尚未完成：** 远端目录列表和对象大小是元数据盘点，不是文件内容 SHA 证明。当前输出目录未发现由 Worker 生成的全量结果 SHA256 Manifest。因此不能声称 33 个输出对象已经完成独立内容哈希验收。只读下载与本地 SHA 清单工具已实现为 `scripts/r60_base336_gpu_result_audit.py`，复用 `r60_base336_gpu_cli._remote_set/_remote_uri` 和 `hf_job_runner.sha256`，不会写入 Bucket、提交 Job 或启动 GPU。Owner Mac 执行前必须有足够空间：若33个对象的远端大小元数据完整，至少为总大小再加1GiB（当前约6.61GB）；若任一对象缺少有效大小，工具保守要求至少8GiB。它会在下载前检查，不足时零下载退出；本地输出目录必须是私有根目录下的新目录。该 Manifest 是下载对象的本地 SHA256 inventory，不是与 Worker 原始逐文件 SHA 的比较，因为本轮 Worker 没有发布原始结果 SHA。

## 4. 为什么 43 条 Validation 不能作为独立质量测试

- 43 条 Validation 已作为本次 `swift sft --val_dataset` 输入，并在 terminal step 37 执行 Eval。
- Trainer state 将 `checkpoint-37` 记录为 best checkpoint，best_metric 为 terminal eval_loss。
- 因此这 43 条已参与训练过程中的 checkpoint/模型选择，不能再称为未触碰的独立 Held-out，也不能用于正式模型晋升结论。
- 293 条 Train 更不能用于独立评测；293+43 的 336 条全部属于本次训练/验证池。
- Worker 只对一个 Validation 样本执行了 `swift infer` 的 128-token Adapter Reload smoke；它证明 Adapter 可加载并产生非空结果，不是完整 43 条生成评估，也没有 Base 对照臂。

R50 密封内容仍禁止读取。R47/R48/R55 已暴露开发题不能重新包装成独立测试。REAL1000/Pilot5 的旧 Reviewer 回执也不能被当成 Base336 生成输出的评测结果。

## 5. 现有工具盘点与复用边界

| 现有能力 | 可复用内容 | 不可直接照搬的原因 |
|---|---|---|
| `scripts/hf_job_runner.py` | `Runner`、`make_inference_input`、`check_inference_result`、`sha256` | 仍需绑定本轮新的输入 Manifest、模型/Adapter 路径和 Job 输出目录 |
| `scripts/prepare_eval_pairs.py` | prompt 前缀对齐、逐案随机 A/B、私有 answer key、create-only | 当前 scorecard 字段是旧五维，不是冻结 Quality-v1 六维 |
| `scripts/analyze_blind_eval.py` / `scripts/export_context_blind_review.py` | 盲化映射与上下文呈现的既有模式 | 使用旧五维评分，且导出器固定 15/20 条，不能直接作为本轮六维审核合同 |
| `experiments/r58_quality/quality_v1.py` | 唯一冻结六维分数门槛与三个严重标记定义 | 这是准入规则，不应复制成另一套评分器 |
| `experiments/r58_quality/r60_real_ai_dual_review.py` | 六维审核指令、决策一致性语义 | 其批次验证器绑定 REAL1000 原始捕获，不应直接伪装成生成结果批次 |
| `src/storyforge_gold_quality/hf_literary_review.py` | 现有引用候选、严格引用校验和六维审核基础 | 当前输入语义明确为 `DB_FINAL_PERSISTED_ASSISTANT`；生成回复不能冒充数据库最终持久化回复 |

下一版只允许做**薄适配器/版本化输入 Schema**：复用 Prompt SHA、结果对齐、随机盲化、私有 answer key、六维 floors 和 severe 语义；不得复制通用 HF Job Runtime、Token/Collator、质量门槛、引用校验或 Manifest。生成结果评估是模型对比证据，不是源数据审核事件，不得向 `storyforge-gold-quality` Manifest 追加伪造的 SOURCE / BLIND_REVIEW / RECONCILIATION 事件。

## 6. 正式独立质量评估的必要条件

1. **新的独立测试来源：** Owner 提供或批准一个未进入本次 336 Train/Validation、未用于调参/Checkpoint 选择、未被 R47/R48/R55 暴露、且不触碰 R50 的来源绑定测试包。建议初始 40–60 个提示、覆盖至少 4 个未使用故事/世界；正式冻结前由 Owner 确认范围、来源权利和世界组件隔离证据。若没有合格来源，质量评估保持 HOLD，不从 661 个未准入候选或数据库中自动抽取。
2. **固定生成合同：** Base 与 Adapter 使用相同的三个可见持久化消息、相同模型 Revision、相同上下文长度、解码参数、停止条件和输出 Token 上限；Adapter 路径固定到本次 checkpoint-37。生成参数必须先在合成测试和 CPU CLI 兼容检查中冻结，不能看过质量结果后反复调参。
3. **独立配对生成：** 每个 prompt 对 Base/Adapter 各生成一次；逐项核对 prompt SHA、消息前缀、输出数量、非空、停止/截断元数据。每案随机化 A/B，映射密钥单独 0600 保存，评审者不可见模型身份。
4. **六维盲审：** 严格复用 `quality_v1.py` 冻结六维门槛（4/4/3/4/4/4）与三个严重标记（`serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion`）；评审只依据给定三消息，不推断隐藏世界设定。保留逐条证据引用、HOLD 不确定性和严重问题，不用旧五维 scorecard 替代。
5. **独立性与裁决：** 评审者必须盲化且执行独立；不同模型 ID 不等于独立。严重标记和世界事实争议由 Owner/独立裁决处理。小样本偏好统计不能被描述为总体提升或生产质量通过。
6. **单独 GPU 推理授权：** 之前授权仅覆盖本 Run Key 的一次探索性训练 Job，不包含 Base/Adapter 配对推理、GPU 评审或新的训练。未来如需 HF GPU inference，须重新提交精确 Job 目的、模型、Flavor、时长、样本数、生成 Token 上限、Bucket RO/RW 前缀和费用范围，等待 Owner 明确批准。

## 7. 下一步顺序与当前决策

| 顺序 | 工作 | 当前状态 |
|---|---|---|
| P0 | 训练 Job / SAFE / Checkpoint / Adapter Reload 证据核验 | PASS |
| P1 | 33 个远端对象的 Owner 本地 SHA 审计（`scripts/r60_base336_gpu_result_audit.py`） | 待Owner执行 |
| P2 | 新的独立测试来源、权限、来源 SHA 与世界隔离确认 | HOLD |
| P3 | 复用既有 Runner / Pairer，完成六维生成评估薄适配器及合成测试 | 等 P2 |
| P4 | Base/Adapter 配对 GPU 推理 | 需单独授权 |
| P5 | 独立盲审、严重标记核验和 Owner 裁决 | 等 P4 |
| P6 | 模型质量结论与是否继续下一轮实验 | HOLD |

**当前最终状态：** `BASE336_GPU_EXPLORATORY_ENGINEERING_PASS__NOT_PROMOTED`。GPU 工程实验成功完成；模型质量尚未得到独立验证。保持 `model_promoted=false`、`train_admitted=0`、`quality_v1_admitted=0`，不追加训练、不启动推理、不访问 R50、不写数据库。


### Owner Mac 只读产物审计命令

```bash
cd ~/workspace/storyforge-r60-4router-review
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
RUN_KEY="r60-base336-gpu-20261117T055622Z-b609cb78661d"
OUT="$HOME/.local/share/storyforge/r60/private/r60-base336-result-audit-$RUN_KEY"
export PYTHONPATH=src:scripts:experiments/r58_quality
"$PY" scripts/r60_base336_gpu_result_audit.py --run-key "$RUN_KEY" --output-dir "$OUT"
```

该命令先只读列举HF Bucket并核对固定33对象清单、磁盘空间和本地私有目录，再逐个下载结果对象到新建私有目录，计算本地SHA256并写0600 Manifest；预计下载约5.61GB。远端大小元数据不完整时会要求至少8GiB空闲空间。下载失败留下的目录不得删除后复用；应先只读检查失败原因并另用新目录。SAFE只报告文件数/字节数，不输出私有路径、文件名、内容或哈希。
