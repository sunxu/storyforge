# R59 Pilot8 语义审核输入适配器（CPU-only）

## 状态及约束

本交付仅用于**构造审核输入**；不提交 GPU，不执行模型推理，不证明文学质量、上下文语义、Reviewer 独立性、世界来源真实性、保护集隔离或 Quality-v1 准入。

源输入：既有 suffix72 Source Stage（含 SAFE 回执）和已冻结 Pilot8 PRIVATE JSON。所有输入要求普通文件、权限 0600；新输出只允许创建在仓库外权限 0700 的父目录。所有私人正文只保留在 Owner 本机。

**重要限制：** 输入适配器保留 Stage 中完整可见历史，不自行裁剪长输入。这意味着某些样本可能远超评审模型的上下文，必须由后续 HF CPU Tokenizer 预检给出确切结果。不能用少量消息裁剪后的评审冒充完整审核，也不能将 R59 通用 System 当作 R58 的 `unapproved_card`。

## 集成位置

将两个 Python 文件放在 `experiments/r58_quality/` 下：

- `r59_semantic_review_adapter.py`
- `test_r59_semantic_review_adapter.py`

本工具与 R58 原有 `r58_hf_gpu_literary_reviewer.py` **尚未连接**。R58 的 13 条输入和 `unapproved_card` 合同不兼容 R59，因此不能直接提交旧 Reviewer。下一步应设计含完整历史覆盖状态的 Prompt 及其独立 fingerprint/checkpoint，复用 R58 严格引用校验的公共逻辑，并先以 HF CPU 测量输入长度。

## Mac 命令

```bash
set -euo pipefail
cd ~/workspace/storyforge-gold-quality
ruff check experiments/r58_quality/r59_semantic_review_adapter.py experiments/r58_quality/test_r59_semantic_review_adapter.py
PYTHONPATH=experiments/r58_quality python -m unittest -v test_r59_semantic_review_adapter

PRIVATE="$HOME/.local/share/storyforge/r59/private"
STAGE="$PRIVATE/source-staging-suffix72-20261104-v1"
PILOT="$PRIVATE/quality-v1/semantic-pilot8-suffix72-20261104-v1/R59_SEMANTIC_PILOT8_PRIVATE.json"
OUT="$PRIVATE/quality-v1/semantic-pilot8-review-input-20261104-v1"
test ! -e "$OUT"
python experiments/r58_quality/r59_semantic_review_adapter.py \
  --staged-jsonl "$STAGE/GOLD_SOURCE_STAGING_PRIVATE.jsonl" \
  --staging-safe "$STAGE/GOLD_SOURCE_STAGING_SAFE.json" \
  --pilot-json "$PILOT" \
  --output-dir "$OUT"
```

仅向聊天回传 SAFE stdout。工具固定状态 `R59_PILOT8_FULL_HISTORY_INPUT_BUILT__TOKEN_PREFLIGHT_PENDING`，输出：

- `R59_SEMANTIC_PILOT8_REVIEW_INPUT_PRIVATE.jsonl`，权限 0600，不得上传公共 GitHub 或发送聊天。
- `R59_SEMANTIC_PILOT8_REVIEW_INPUT_SAFE.json`，权限 0600，只含计数与私人数据文件 SHA256；如需回传，优先仅回传 stdout 的聚合字段。

## 验收记录

R59 Tokenizer Runner 的合成单元测试：7/7 PASS；R60 专项 GitHub CI 已执行 Ruff、Compile、Runtime/Volume、Skill 合同、R59 适配器及共享 Tokenizer 核心回归，全部通过。最新 Mac 本地回归仍须在 Owner 本机按 R60 handoff 命令复核。未使用真实 R59 私有材料，未运行本轮 R59 HF CPU Tokenizer Job、GPU 或 Quality-v1 准入。

## R60 Runtime 集成（CPU Tokenizer Runner）

R60 迁移后，`r59_semantic_prompt_token_cpu.py` 使用公共 Runtime 执行环境识别、CPU 资源检查、输入 no-follow/限长读取、SAFE create-only 原子写入和 Runtime 诊断回执校验；Tokenization 算法仍唯一复用 `src/storyforge_dataset/token_preflight.py`，不复制核心。

HF Job 必须先安装与 Runner 同一 Commit 的 StoryForge 源码包，使 `storyforge_dataset.hf_runtime` 可导入；独立挂载的 `token_core.py` 必须与 `src/storyforge_dataset/token_preflight.py` 字节一致。Runner 必须识别为 `HF_JOB`，并由 `ResourceGuard` 在 Tokenizer 导入前后检查 CPU profile。

新增必需参数：`--runtime-diagnostic-safe`，写出独立的 `storyforge-hf-runtime-diagnostic-v1` 回执。原有 R59 业务 SAFE Schema 不变；两个 SAFE 文件均 create-only，输出到独立私有 RW 目录。下载后分别校验业务回执和 Runtime 回执，不能以其中一个代替另一个。

示例执行（仅在已批准的 R59 HF CPU Job 中使用；所有占位路径和模型版本必须来自当前冻结输入/Runbook，不得自行替换）：

```bash
python experiments/r58_quality/r59_semantic_prompt_token_cpu.py \
  --input /job/R59_SEMANTIC_PILOT8_REVIEW_INPUT_PRIVATE.jsonl \
  --model <APPROVED_MODEL_ID> \
  --revision <IMMUTABLE_40_HEX_REVISION> \
  --max-model-len 32768 \
  --reserved-output-tokens 2400 \
  --output-safe /results/R59_PILOT8_TOKEN_SAFE.json \
  --runtime-diagnostic-safe /results/R59_RUNTIME_DIAGNOSTIC_SAFE.json
```

`R59_INPUT_SHA256` 与 `R59_PROMPT_FINGERPRINT` 应作为 HF Job protected secrets 注入环境；不要将私有输入指纹写进 Job command、GitHub、stdout 或普通日志。Runner 要求两个 SAFE 输出在同一已存在的 RW 目录中，且文件名不能已存在。

合成回归命令：

```bash
PYTHONPATH=experiments/r58_quality python -m unittest -v test_r59_semantic_prompt_token_cpu
```

此迁移不访问真实 R59 私有输入，不改变冻结 Prompt、Pilot8 选择、模型 Revision 或预算；真实 R59 Tokenizer CPU Job 仍需单独通过本地门禁后执行。
