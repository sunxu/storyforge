# R59：Gold72 连续历史后缀重建（非训练准入）

日期：2026-11-04。本页记录 Owner 实测聚合数据和经确认的后续主线，不触发训练或 GPU。

## 实测结论

`r59_history_structure_diagnostic.py`：72 条来源中原样全历史结构合法 5 条，67 条 HOLD；存在空文本 67 条、非 completed 状态 67 条、连续角色 33 条。合计消息 138,988 条（其中 completed 138,058，其他字符串状态 930）。

`r59_history_recovery_probe.py`：假设仅排除未完成且为空的消息，67 条仍不能通过结构检查（51 条过滤后角色连续；16 条另有障碍），此外共有 completed 但内容为空 185 条。

`r59_contiguous_suffix_probe.py`：**72/72 均有连续、未改写、严格交替、completed 且非空、以 User 结尾的历史后缀，且长度都不少于 8 条消息**。原样完整合法 5；原样连续后缀 67；至少 16 条消息的后缀有 69 个候选。长度桶：8–15 为 3、16–31 为 6、32+ 为 63。这里是「消息条数」而非 Token 数。

## 已新增 Source Stage v2

`experiments/r58_quality/r59_contiguous_suffix_stage.py` 在 Owner 本地使用：
1. 冻结的 `R59_SOURCE_CONTEXT_PRIVATE.jsonl`；
2. 原先的 `GOLD_SOURCE_STAGING_PRIVATE.jsonl`；
3. 与其配套的 `GOLD_SOURCE_STAGING_SAFE.json`。

先检查来源文件 SHA 和既有 Stage 字节 SHA 与旧 SAFE 一致；从原先成功 Staging 的 System 提取经过原 SAFE SHA 固定的同一文本；对每条原始 history，只保留**以当前 User 结尾的最长、完全原样且连续**历史后缀；再次调用既有 `stage_source()` 全部结构规则，并逐项验证原先五条 Ready 样本消息 SHA 不变。新 Staging 中每条记录额外留存原始 history、连续后缀的 SHA256、原历史条数、保留条数和移除的前缀条数。所有这些逐案私有字段只保存在 0600 JSONL 中。不会实际修改原始来源或旧 Staging，也不会将空白/失败消息与旁边消息拼接。

输出新的私有 `GOLD_SOURCE_STAGING_PRIVATE.jsonl` 和 SAFE；与旧文件同名但位于新目录。所有数据在真实执行前仅为代码/合成测试候选。输出 `quality_v1_admitted=0`、`training_authorized=false`。这种结构恢复**不证明**被截前缀没有重要剧情设定；须经过真实故事/世界语义审核才能成为 Gold 训练样本。

## Mac 运行（仓库根目录，venv 已激活）

```bash
set -euo pipefail
git pull --ff-only origin gold-quality/quality-v1-sft-candidates
ruff check experiments/r58_quality/r59_contiguous_suffix_stage.py experiments/r58_quality/test_r59_contiguous_suffix_stage.py
python -m unittest discover -s experiments/r58_quality -p 'test_r59_contiguous_suffix_stage.py' -v

PRIVATE="$HOME/.local/share/storyforge/r59/private"
SOURCE="$PRIVATE/r59-source-priority72-20261103/R59_SOURCE_CONTEXT_PRIVATE.jsonl"
OLD="$PRIVATE/source-staging-priority72-20261103"
NEW="$PRIVATE/source-staging-suffix72-20261104-v1"
test ! -e "$NEW"

python experiments/r58_quality/r59_contiguous_suffix_stage.py \
  --source-context-jsonl "$SOURCE" \
  --previous-staged-jsonl "$OLD/GOLD_SOURCE_STAGING_PRIVATE.jsonl" \
  --previous-staging-safe "$OLD/GOLD_SOURCE_STAGING_SAFE.json" \
  --output-dir "$NEW"
```

请只反馈最终 SAFE JSON，尤其 `context_staged`、`original_ready_unchanged`、`previously_held_now_structurally_staged` 与 `staged_file_sha256`；不要发送 PRIVATE JSONL。任何 Ruff/测试或真实执行失败时保留 HOLD，不自行绕过。

## 后续质量/训练主线

- 使用新的 Source Stage 72 条重新做 Gold192 的审核定位、Owner Evidence 工作副本；旧五条模板不能视为新 72 条完整审核。
- A/B 真实逐案六维评分、Owner 严重问题补查、世界组件隔离、保护集排除、来源 pin 仍需实际证据；未知不补写“通过”。如果部分字段过于依赖无必要的生产请求精确回放，应单独评估是否调整门禁，不能由本脚本默许。
- 已批准的通用无世界卡 System 只用于新训练输入，不宣称历史生产复现。
- Quality-v1 正式准入、Train/Validation 冻结和 HF CPU 16K/tokenizer/collator **仅针对最终审核通过的训练集** 执行。
- GPU LoRA 仍须单独明确授权；R50 held-out 不得访问、无 GPU 自动提交。
