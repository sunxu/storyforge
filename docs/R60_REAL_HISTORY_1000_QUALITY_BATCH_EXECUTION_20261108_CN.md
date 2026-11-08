# R60-REAL 第二阶段：1,000 条真实候选批量 AI 质量审核（2026-11-08）

## 实际已完成的前置阶段

Owner Mac 最终 SAFE 回执：
- `status=EXPANSION_TARGET_REACHED__NOT_ADMITTED`
- `seed_cases=6`、`new_cases=994`、`total_candidates=1000`
- `private_pages=20`、`stories_scanned=400`
- `quality_pass=0`、`train_admitted=0`
- `r50_body_accessed=false`、`r50_complete_exclusion_verified=false`、`world_isolation_verified=false`
- `database_modified=false`、`gpu_started=false`、`private_values_emitted=false`

**第一阶段已完成。停止扩样。** 目标转为对冻结池进行真实文本质量评价，拟从中筛选高质量候选，不以 200–400 PASS 作为必须凑数的指标。现阶段仍不得将技术候选称为可训练数据。

## 新批量工具

`experiments/r58_quality/r60_real_quality_batch.py`，三个子命令：
- `init`：只读校验原 Seed、每一页 JSON/来源哈希、600→1000 不可改扩容回执及最终**精确 1,000 条**状态；记录私有池指纹和两个独立模型的本地 API 配置，创建新的私有批量审核目录，不覆盖原 20 页。
- `advance`：默认一次审核 5 条、最多 25 条；每条发送两个互不共享结论的 AI 请求，并对评分 Schema、六维最低分、严重越权/事实冲突/安全问题做校验。单案例完成后立即持久化一份**只增不覆盖**的 0600 私有回执，随时可中断恢复。模型无效输出不补造评分，保留完整已完成部分作为 HOLD；两个模型同时传输失败时直接停止并保留既有案例，避免 1,000 条全部误判为审核失败。
- `inspect`：不需要 DSN 或模型在线。逐条核对冻结池指纹、审核记录位置、目标/历史 SHA、回执校验、Reviewer ID、模型来源、评分与决定规则，输出只含 PASS/HOLD/REJECT 计数和固定错误码的 SAFE，不回传私有正文/ID/哈希/理由。

六维：`chinese_prose`、`character_consistency`、`npc_initiative`、`player_agency`、`rule_fidelity`、`narrative_continuity`。三项严重旗标：`serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion`。任一模型严重拒绝需排除；无完整双审的案例为 HOLD。

**独立性边界**：两种模型标识不同且调用过程不共享另一方结论，但这无法证明模型训练数据/实际运营机构独立，也不相当于独立人类审核。默认 `owner_attested_independent_ai=false`，即使两次打高分仍 HOLD；仅当 Owner 确认实际调用两种独立模型并隔离评审后，可显式使用 `--owner-attest-independent-ai`。这个标志仅供实质审阅流程确认，不能自动满足 R50/world/CPU/训练授权条件。

**上下文边界**：当前每案只有目标前 3 条真实历史消息；本步只能评估局部可见规则与上下文。缺失历史完整世界/System 时不可凭空断言全局无矛盾。旧 `R60_REAL_G1_CAPTURE_PRIVATE.jsonl` 与新的 20 个批次页均不修改。

## Owner Mac：先小批真实审核，再按需继续

先在 StoryForge repo 根目录同步 R60 最新工作分支：

```bash
set -euo pipefail
set +x
umask 077
git fetch origin r60/gold192-history-v3-adapter
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter

BASE="$HOME/.local/share/storyforge/r60/private"
EXPAND="$BASE/r60-expand-first-600"
QUALITY="$BASE/r60-quality-first-1000"

python3 experiments/r58_quality/r60_real_expand_private.py inspect --output-dir "$EXPAND"
test ! -e "$QUALITY"
```

必须先核对 `inspect` 是 `EXPANSION_TARGET_REACHED__NOT_ADMITTED`、`total_candidates=1000`。本次**不用重新 `init` 扩样器，不需要数据库 DSN**。

示例本机 OpenAI-compatible endpoint。先用 `ollama list` 核对 Owner Mac 确实已安装**两种不同的模型**；下面的名称仅是示例，不能凭空假设已经安装：

```bash
python3 experiments/r58_quality/r60_real_quality_batch.py init \
  --expand-dir "$EXPAND" \
  --output-dir "$QUALITY" \
  --endpoint-a http://127.0.0.1:11434/v1 \
  --model-a qwen3:14b \
  --endpoint-b http://127.0.0.1:11434/v1 \
  --model-b gemma3:12b \
  --json-mode \
  --owner-attest-independent-ai
```

`--owner-attest-independent-ai` 只能在你确已验证两个模型独立执行时使用；否则省略，SAFE 会显示质量 HOLD。若需审阅云端 AI API，必须对每个远程 URL 使用 HTTPS，主动加 `--allow-remote-review`，并确认私有 User/Assistant 内容将传给该提供商；各自 API Key 只由 `R60_REVIEW_A_KEY` / `R60_REVIEW_B_KEY` 环境变量提供，不能写入 Shell 参数、GitHub、SAFE 或聊天。

先运行只含 5 条的**受控校准批**：

```bash
python3 experiments/r58_quality/r60_real_quality_batch.py advance \
  --output-dir "$QUALITY" --max-cases 5

python3 experiments/r58_quality/r60_real_quality_batch.py inspect \
  --output-dir "$QUALITY"
```

观察 `cases_reviewed`、`quality_decisions` 和 `model_attempt_hold_counts`。若出现 `BOTH_REVIEW_MODELS_UNAVAILABLE`，排查本地模型/兼容端点；不会丢弃之前成功存储的案例，也不需重建原始池。模型输出非结构化 JSON 或质量不合格时保持 HOLD/REJECT，不能用默认高分补齐。

校准合格后可渐进推进，每次上限 25 条，直到 `QUALITY_BATCH_REVIEWED__TRAIN_ADMISSION_HOLD`（在已配置的 2 模型推理资源可用前提下会进行多次本地推理，需考虑算力/远程 API 费用）；建议分段查看 SAFE 而不是一开始提交全量不受控任务：

```bash
for i in 1 2 3 4; do
  python3 experiments/r58_quality/r60_real_quality_batch.py advance \
    --output-dir "$QUALITY" --max-cases 25
done

python3 experiments/r58_quality/r60_real_quality_batch.py inspect \
  --output-dir "$QUALITY"
```

## 后续门槛（不自动开启 GPU）

1. 统计 Quality 真实 PASS/HOLD/REJECT、玩家自主权严重违例等；随机抽查 AI 误判并制定复核策略。
2. 对质量候选做完整 R50 **元数据级**集合和独立世界组件验证，不能读取 R50 正文。
3. 通过目标前真实历史、模型输入重建约束、世界 Split、Qwen Tokenizer 和 ms-swift Collator CPU 预检，制作冻结训练集。
4. 申请 Owner 明确授权 HF GPU 训练。禁止自动运行 GPU。

**截至这份执行书提交：本次 Owner 的 1000 条真实采集已完成；新的 AI 批量审阅代码和合成测试已落地，但真实 AI 评审尚未在 Owner Mac 执行，质量 PASS 仍为 0、训练准入仍为 0。**
