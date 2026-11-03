# StoryForge R59 — 从 Gold Quality-v1 进入 SFT 候选编译（非训练准入）

日期：2026-11-03。主线：高质量中文互动剧情 LoRA。历史 Supabase Ledger 的精确事件回放不再是新训练候选的前置条件；历史 R59 HOLD 保留归档，不能谎称历史来源审计 PASS。

## 已交付代码

- `experiments/r58_quality/quality_v1_sft_candidates.py`：直接调用冻结的 `quality_v1.py` 校验函数，不重新实现质量六维评分，不凭空生成 Reviewer / Owner 证据。
- `experiments/r58_quality/test_quality_v1_sft_candidates.py`：只使用原创合成记录验证，通过/拒绝、Assistant-first、最后目标唯一 loss、世界隔离、重复哈希、私有文件 0600 和不可覆盖。
- 专项 GitHub Actions 自动运行 Ruff 与合成回归；不启动 HF / GPU，不读取 R50。

### 输入合同

必须是私有 `storyforge-quality-v1-private-candidate-v1` JSONL；原始 Gold、Reviewer A/B 的分数、上下文已审核声明、保护隔离核验和独立源 pin 必须从 Owner 实际证据构建。脚本不会根据 Gold192 的统计数量自动生成审核通过记录，也不会把历史 Reviewer 的 PASS 自动转换为质量准入。使用 `quality_v1.py` 的 `decide()` 及 `summarize()` 执行全体重复与跨世界隔离检查。

输入文件必须是普通文件，不是 symlink，权限为 0600；最多 195 条。建议先从有可信私有证据的 Strict28 / Gold72 候选生成输入，缺少 Evidence 的记录应保持 HOLD，不得补全虚假字段。

### 本机运行（不访问数据库）

在 Gold Quality 分支工作树、现有项目 venv 下：

```bash
PRIVATE="$HOME/.local/share/storyforge/r59/private"
INPUT="$PRIVATE/quality-v1/OWNER_REVIEWED_GOLD_CANDIDATES.jsonl"
OUT="$PRIVATE/quality-v1/sft-candidates-20261103-run1"
test -f "$INPUT"
test ! -e "$OUT"
.venv/bin/python experiments/r58_quality/quality_v1_sft_candidates.py \
  --private-reviewed-jsonl "$INPUT" --output-dir "$OUT"
```

`PRIVATE/quality-v1` 须预先由 Owner 创建为 0700 目录；产物本身不会覆盖任何已有文件，也不能写在 Git checkout 内：

- `SFT_CANDIDATES_PRIVATE.jsonl` — 当前通过结构与审核声明门禁的候选消息（含 last-assistant-only loss 标记）及内部身份字段；权限 0600。
- `SFT_CANDIDATES_SAFE.json` — 仅聚合统计与私有文件 SHA256，不含剧情、Case ID 或世界 UUID。

### 准入与训练门禁

`PRIVATE_SFT_CANDIDATES_BUILT__NOT_QUALITY_ADMITTED` **不等于** `QUALITY_V1_ADMITTED`。当前 `quality_v1_admitted=0`、`dataset_frozen=false`、`tokenizer_collator_checked=false`、`training_authorized=false`、`gpu_started=false`。必须后续逐条核实私有 Reviewer A/B 的来源独立性、上下文质量及世界隔离，生成经 Owner 核对的实际准入名单，然后冻结 Train/Validation，并在 HF CPU 做 Qwen tokenizer + ms-swift collator 的真实预检。禁用 R50 题文访问和自动 GPU 提交。

不要强制要求复现原生产 System Prompt；现有无世界卡 System Prompt 方案可以用于明确标记的训练上下文编排，但本脚本只消费已准备并校验的 `messages`，不杜撰角色世界卡，也不写入生产数据库。
