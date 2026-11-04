# R59 16K 上下文窗口重建工具

> 本文记录 R59 工程预检阶段的上下文窗口重建流程。此流程不等于 Quality-v1 准入，不冻结正式数据集，也不授权训练。

## 1. 目的与边界

R59 五条 Shape Preview 的首次实际 Token 测量结果为：

| 指标 | 结果 |
|---|---:|
| Preview 数量 | 5 |
| 原始上下文不超过 16,384 tokens | 3 |
| 原始上下文超过 16,384 tokens | 2 |
| Token 中位数 | 13,660 |
| Token P95 | 34,263 |
| 最大长度 | 114,558 |

不能对超长样本做字符截断、Token 截断，也不能删除中间消息。应保留最近的连续对话窗口，同时保证 System Prompt、当前 User 输入和最终目标 Assistant 回复完整。

工具：`experiments/r58_quality/r59_sft_context_window.py`

测试：`experiments/r58_quality/test_r59_sft_context_window.py`

## 2. 固定输入与算法

- 模型：`Qwen/Qwen3.8-27B`
- 固定 Revision：`1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`
- Token 上限：`16384`
- ms-swift：`4.5.3`
- Transformers：`5.16.1`
- 监督策略：`last_round`

重建规则：

1. 原始 Shape Preview 只读，绝不覆盖。
2. System Prompt 内容必须通过现有 R59 Preview Validator 的固定 SHA 检查。
3. 首先测量完整历史；完整历史能容纳时，原样保留。
4. 超限时，只能从历史开头删除连续前缀；保留窗口必须从完整 User 消息边界开始。
5. 删除前缀之后的所有消息按原顺序连续保留，不得删除中间消息。
6. 最终 User 输入和目标 Assistant 回复必须完整保留。
7. 历史消息全部保持 `loss=false`，只有最终目标 Assistant 保持 `loss=true`。
8. 保留原始 `input_messages_sha256` 为 `source_input_messages_sha256`，并对新上下文重新计算 `input_messages_sha256`。
9. 任一条样本无法在不截断当前 User 或目标回复的前提下满足预算，整批 HOLD，不输出部分候选。
10. 重建后必须调用现有实际 ms-swift Collator 再验一次；Token 长度通过不能代替 Collator 通过。

Token ID 提取必须复用 `src/storyforge_dataset/token_preflight.py` 中的 `extract_input_ids`。独立 HF Job 运行时，脚本目录中的 `token_core.py` 必须是该源文件的逐字节副本，不得重新实现 Token 提取逻辑。

## 3. HF CPU Job 执行

运行环境必须是 HF CPU Job，不在 Mac 本机测量模型 Token 长度。设置：

```bash
export CUDA_VISIBLE_DEVICES=""
export USE_HF=true
export TOKENIZERS_PARALLELISM=false
python3 -m pip install --no-cache-dir \
  "ms-swift==4.5.3" "transformers==5.16.1" \
  "qwen-vl-utils==0.0.14" decord "torchvision==0.29.2"
```

提交前保护工具 `scripts/hf_job_guard.py` 允许只读输入挂载到精确目录根 `/input`、`/scripts`，也允许其下的路径 `/input/...`、`/scripts/...`。此前版本只允许带末尾斜杠的子路径，导致目录前缀挂载在尚未提交 Job 时返回 `INPUT_DESTINATION_MUST_BE_INPUT_OR_SCRIPTS`。这属于 Guard 契约错误，不是 Bucket 数据或组织权限错误。已增加目录挂载及相似路径拒绝回归测试。只读输入 `:ro`、独立可写输出 `:rw` 等限制保持不变。

输入、脚本使用目录前缀只读挂载，不要把文件路径误当成挂载目录：

- 私有输入目录：`hf://buckets/adradar/storyforge-training/preflight/r59/20261103:/input:ro`
- Worker 脚本目录：`hf://buckets/adradar/storyforge-training/scripts:/scripts:ro`
- 脚本目录包含 `r59_sft_context_window.py`、`r59_sft_collator_cpu.py` 和精确副本 `token_core.py`。
- SAFE 输出需要单独、唯一的可写输出前缀；ChatGPT Connector 的 RW 403 与 Mac CLI 的权限状态必须分开判断。

运行前：

```bash
test -f /input/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl
test -f /scripts/r59_sft_context_window.py
test -f /scripts/r59_sft_collator_cpu.py
test -f /scripts/token_core.py
```

将只读挂载的输入复制为普通私有文件，再执行工具：

```bash
cp /input/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl /tmp/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl
chmod 600 /tmp/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl
mkdir -m 700 /tmp/r59-context-output-parent
python3 /scripts/r59_sft_context_window.py \
  --private-input /tmp/R59_SFT_SHAPE_PREVIEW_PRIVATE.jsonl \
  --output-dir /tmp/r59-context-output-parent/attempt-01
```

输出目录必须位于系统临时目录，父目录权限为 0700，目标目录必须不存在。工具采用 create-only 写入；私有 JSONL 和 SAFE JSON 文件权限均为 0600。不得把输出目录设在 Git 仓库中。

如果需要持久化到 Bucket，必须在 Job 成功后，将文件复制到一个全新的唯一输出前缀。不能覆盖已有证据。ChatGPT Connector RW 403 时，不得通过扩大输入挂载权限规避；按项目规范使用受保护的 Mac-local CLI 路径。

## 4. SAFE 状态解释

成功状态：

`R59_CONTEXT_WINDOW_AND_COLLATOR_PASS__NOT_ADMITTED`

该状态仅表示：

- 每条输入都在 16,384 Token 预算内；
- 历史窗口重建规则通过；
- 实际 ms-swift `last_round` Collator 通过；
- 目标监督位置和 loss mask 符合预期。

它不表示文学质量通过、Quality-v1 正式准入、Train/Validation 集合冻结或训练授权。

任何阶段都必须保持：

```json
{
  "quality_v1_admitted": 0,
  "dataset_frozen": false,
  "training_authorized": false,
  "gpu_started": false,
  "training_performed": false,
  "private_values_emitted": false
}
```

## 5. 2026-11-04 正式验证记录

正式执行 Job：`6aea1d8e0e0338d1bb7f6336`

结果：`R59_CONTEXT_WINDOW_AND_COLLATOR_PASS__NOT_ADMITTED`

| 样本 | 原历史消息数 | 删除前缀消息数 | 保留消息数 | Token |
|---:|---:|---:|---:|---:|
| 1 | 299 | 156 | 143 | 16,384 |
| 2 | 67 | 0 | 67 | 12,963 |
| 3 | 509 | 446 | 63 | 16,288 |
| 4 | 27 | 0 | 27 | 3,482 |
| 5 | 121 | 0 | 121 | 13,660 |

实际 Collator：5/5 PASS；模型 Revision 固定；CPU only。

该 Job 在临时工作区验证了私有输出目录 0700、私有 JSONL 和 SAFE JSON 0600。Job 只保留 SAFE 聚合日志，私有 JSONL 没有回传聊天，也没有写入持久 Bucket。因此本次验证证明正式工具能够执行，但尚未产生可供后续训练使用的持久冻结数据集。

同日静态检查与合成回归：

- Ruff：3 个 Python 文件检查通过。
- 上下文窗口测试：8/8 PASS。
- 现有 Collator 测试：10/10 PASS。
- Python compileall：PASS。
- GitHub Actions 仍因 Runner 未启动、Job steps 为空而无法完成 CI 复核；不能将其标记为 GitHub CI PASS。

## 6. 后续步骤

1. 将 PR #11 中正式工具、现有 Collator 和共享 Token 核心同步到私有 Bucket。
2. 使用新的唯一输出前缀，重新运行正式 CPU Job，并持久化 PRIVATE JSONL 与 SAFE JSON。
3. 对持久化产物核验 SHA256、文件权限、源输入哈希、目标哈希及实际 Collator SAFE 回执。
4. 再进入正式候选数据集构建与 Quality-v1 准入；不得从本次 Preview 工程 PASS 直接推导训练准入。
