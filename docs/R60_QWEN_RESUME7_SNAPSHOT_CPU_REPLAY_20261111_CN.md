# StoryForge R60 — Qwen A25 第7条 Snapshot + CPU Replay 工程交接（2026-11-11）

## 已确认事实

- Owner CPU Gate 实测 `QWEN_RESUME7_CPU_GATE_PASS`、`checkpoint_prefix_verified=6`、`next_position=7`，未启动 GPU。
- 六份 Checkpoint 的私有原始副本位于 `$HOME/.local/share/storyforge/r60/private/qwen-a25-prefix6-20261111T073158Z`，不得覆盖、修改或作为新生成输出目录。
- 原 A25 输入 SHA：`492f24f7cb6171481e0e6d176cfa862ec6f5223bdd7abc3cfb518335dc9ab069`；模型 `Qwen/Qwen3-32B`，revision `9216db5781bf21249d130ec9da846c4624c16137`。
- 原第7条错误是 `ValueError / UNKNOWN_REVIEW_FAILURE`，具体阶段仍未知。GLM B25 的现役 H200 Job 独立，不得干扰。

## 新增/修改代码

- `r60_qwen_guidance_diagnostic.py`：在 `--diagnose-generation-stages` 下额外输出 `VALIDATE_RESPONSE_*`、`QUOTE_REPAIR_*`、`CHECKPOINT_WRITE_*` 的 SAFE 事件。只输出固定事件名与异常**类型**；不打印异常正文、输入、模型输出、blind ID 或文件路径。钩子退出时恢复原始函数。
- `r60_qwen_continuous_review.py`：新增 `--generation-snapshot-dir`；仅允许显式 `--diagnose-generation-stages --resume --case-limit 7 --batch-size 1` 的第7条诊断。一次 vLLM engine，`generate()` 返回后、校验前先通过 `r60_generation_snapshot.GenerationSnapshotStore` 排他持久化原始 slot01（如有后续 quote repair，slot02）。
- `r60_qwen_snapshot_cpu_replay.py`：纯 CPU 读取第7条签名主 Snapshot，在冻结 Runner 的 `checkpoint_record` 上执行严格技术校验，输出 SAFE 计数及真实质量决定（仅审核有效时）。若存在 slot02，将验签但不会擅自把二次修复结果认作严格主审核通过。
- 新合成测试：`tests/test_r60_qwen_reviewer_stage_trace.py`、`tests/test_r60_qwen_snapshot_cpu_replay.py`。测试内容包括钩子恢复、异常隐私安全、签名快照验签、篡改拒绝、JSON 不合法、finish_reason 不完整、外来文件拒绝。

## GPU 成本护栏

1. 不允许旧版 `--diagnose-generation-stages` 无 Snapshot 就再次付费重试；必须确认新代码的所有 CI PASS 和 Owner 本机完整 CPU 合成测试。
2. Owner 自行执行 HF CLI，且明确支付授权后才提交；ChatGPT 不提交 HF Job。第7条只使用经 CPU 门槛校验过的六份 Checkpoint **新复制副本**，在新的 Run ID 和结果目录中恢复第7条；绝不指向历史原目录写入。
3. Snapshot 目录必须全新且为空；与结果目录独立，不清理失败时的证据。未知异常/引擎错误 HOLD，绝不自动重复生成。
4. 若第7条 `generate()` 已成功但 Reviewer 失败，保留原始生成快照，通过纯 CPU Replay 进行反复诊断，不再为同一条原始输出重复支付 GPU。
5. 若异常在生成前出现，则不会存在可重放的模型输出；根据安全阶段事件判断应继续 CPU Debug 还是由 Owner 另行授权有界 GPU 实验。
6. `quality_v1_admitted=0`、`training_authorized=false`，CPU 严格 Replay 技术有效不构成训练准入。

## Owner CPU 测试（零 GPU）

在 Mac 上先 `git fetch origin r60/p4-generation-eval-framework`，固定最终 CI 全 PASS 的 **完整 HEAD**，然后：

```bash
cd "$HOME/workspace/storyforge"
python3 -m unittest discover -s tests -p 'test_r60_qwen_*trace.py' -v
python3 -m unittest discover -s tests -p 'test_r60_qwen_snapshot_cpu_replay.py' -v
```

如需要用已冻结的私有输入做零 GPU 路径检查，沿用已验收的 `r60_qwen_resume7_cpu_gate.py`；不应把合成测试 PASS 当成真实第7条生成成功。

## 下一门槛

- 四组 CI PASS；
- Owner 本地上述 CPU tests PASS；
- Qwen 专用入口/容器与本次 HEAD 的一致性核验；
- 旧六份回执复制到新目录后重新验证前缀；
- 单次有界付费运行命令经 Owner 明确批准；
- 真实第7条签名 Snapshot 与阶段事件回传；
- 原封不动进行 CPU Replay，禁止训练准入自动升级。

## 2026-11-11 补充：真实 Owner CPU 单测通过与恢复前缀止损保护

Owner Mac 对 `40dbc2d7574b34d18e26bc46cca511dff0ef57a8` 回传：阶段追踪 3/3、Snapshot Replay 5/5、`py_compile` 全 PASS。该提交的四组 CI 后续也已核实全部 SUCCESS。

审查时发现：此前新 Snapshot 运行路径虽要求 `--resume --case-limit 7 --batch-size 1`，但缺少“已验证的前缀必须**恰好6份**”运行时保护。修复后 `run_batches` 在接触 tokenizer/LLM 前验证前6份原版 Checkpoint，任何0–5份或7份以上场景均 `QWEN_SNAPSHOT_RESUME_PREFIX6_HOLD`，不许从位置1重复付费生成。新增纯 CPU 负面测试（0份、5份）验证 GPU 初始化/推理调用次数为0。

该新增保护提交为 `84e7a2bfc078a9dffcf7aebb1b01cf396da7677d`，测试提交为 `a459e812839f3e744d139c35f97e110bea19a9a3`。**必须核对包含这两项的最终文档 HEAD 四组 CI 全 PASS，才能作为新付费代码 PIN；原 `40dbc2d` 不包含恢复前缀运行时保护，不再推荐作 GPU PIN。** Owner 本地合成测试结果来自旧 PIN，新增负面测试仍需 Owner 单独验收。
