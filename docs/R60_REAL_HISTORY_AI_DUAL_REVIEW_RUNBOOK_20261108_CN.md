# R60-REAL-02：已采集 6 条真实历史样本的 AI 双模型审阅执行书（2026-11-08）

## 前提：Owner 的真实采集已经成功，不得重新抽样

Owner Mac 于 2026-11-08 返回：
- `EXACT_G1_CAPTURED__INDEPENDENT_REVIEW_PENDING`：6 条真实样本 / 6 个不同 Story，数据库写入 0，GPU 训练启动 0；
- `PRIVATE_REVIEW_TEMPLATE_CREATED__REVIEWS_UNFILLED`：6 份未填写审核模板；
- 本机 0600 私有文件：`R60_REAL_G1_CAPTURE_PRIVATE.jsonl`（29562 bytes）、`R60_REAL_G1_CAPTURE_SAFE.json`、`R60_REAL_G1_REVIEWS_PRIVATE.jsonl`。

这是**真实生产采集成功**，不再沿用旧报告中「Owner capture 未执行」的过时状态。Owner 已确认真实历史数据可用于 R60 训练，后续不再调查协议问题。下一步必须基于**原已冻结私有文件**实施独立 AI 质量审核，不重复调用 Supabase 或重新产生随机 case key。

代码位于：
- `experiments/r58_quality/r60_real_ai_dual_review.py`（本轮新增）
- `experiments/r58_quality/test_r60_real_ai_dual_review.py`（12 项合成测试）
- 原有 `experiments/r58_quality/r60_real_private_batch.py review`（审核聚合、质量 PASS 但不入训）

## AI 双评审要求

本地执行器使用 OpenAI-compatible `/v1/chat/completions` 接口，对已冻结的每个案例分别请求**两个不同的模型标识**，两个模型不互相看到评分，模型输出必须满足六维 1–5 分、三项严重缺陷布尔值及明确 PASS/HOLD/REJECT。严格拒绝结构缺项、严重缺陷却标为 PASS、低于分数下限仍标 PASS、伪造模型输出等情况。

这是一种可复核的**双模型 AI 评审**，而非人类审核；脚本不证明两模型训练数据独立、机构独立或 Reviewer 在现实世界中的独立性。默认 `reviewers_independent_owner_attested=false`，因此两模型评审不自动满足原独立 Reviewer 质量门槛。Owner **在确认调用的是两个不同模型、无共享审阅上下文**之后，才可显式追加 `--owner-attest-independent-ai`。脚本会验证模型标识不同。质量 `PASS` 仍然 `train_admitted=0`，不能绕开 R50/world/CPU。

默认仅允许 `localhost` / `127.0.0.1` / `::1` 的模型接口；不转发代理，不跟随 HTTP 重定向，避免私有文本被意外发送到外部。使用外部模型服务，必须同时选择 HTTPS endpoint 和显式 `--allow-remote-review`；使用者须知晓此时会将目标前历史和目标正文提交给该模型服务。脚本绝不在 stdout/stderr 打印正文、真实 ID、case_key、SHA、路径、API 密钥或模型回复。

## Owner Mac 执行：不需要 DSN，不重做 capture

先在 StoryForge 仓库同步 R60 分支最新代码。选择**已成功的原目录**，下面 `RUN` 必须是实际包含上述三个文件的目录。不要再运行 `capture` 或 `template`。

```bash
set -euo pipefail
set +x
umask 077
git fetch origin r60/gold192-history-v3-adapter
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter

BASE="$HOME/.local/share/storyforge/r60/private"
# 根据本机已完成的 capture 确定 RUN，替换下方目录名：
RUN="$BASE/g1-pilot-实际时间戳"
test -f "$RUN/R60_REAL_G1_CAPTURE_PRIVATE.jsonl"
test -f "$RUN/R60_REAL_G1_REVIEWS_PRIVATE.jsonl"
test ! -e "$RUN/R60_REAL_G1_AI_REVIEWS_PRIVATE.jsonl"
```

本地模型示例（仅当 Owner Mac 上已经运行兼容接口，并且这两个模型均已安装时才可直接使用；模型名称按 `ollama list` 或本地接口的模型列表替换）。例如使用本机 OpenAI-compatible Ollama `11434/v1`，可在 Mac 本地串行完成 12 个请求；这只是**本地模型推理**，不是 HF/GPU 训练：

```bash
python3 experiments/r58_quality/r60_real_ai_dual_review.py \
  --capture-dir "$RUN" \
  --endpoint-a http://127.0.0.1:11434/v1 \
  --model-a qwen3:14b \
  --endpoint-b http://127.0.0.1:11434/v1 \
  --model-b gemma3:12b \
  --timeout 180 \
  --owner-attest-independent-ai
```

若本地 OpenAI-compatible 端点需要 JSON mode，可增加 `--json-mode`。上述模型名称仅为示例，必须以本机**实际可用**的两种模型为准。相同模型通过两个不同 endpoint 运行会被拒绝；响应格式不合规则整批 HOLD，不产生半成品。若未验证模型隔离，请先省略 `--owner-attest-independent-ai`，SAFE 会显示全部质量为 HOLD。

远程 API 可选：使用两个独立模型的 HTTPS endpoint，命令上明确添加 `--allow-remote-review`；API 密钥只能经环境变量 `R60_REVIEW_A_KEY`、`R60_REVIEW_B_KEY` 提供，不写进命令、仓库或 Issue。**任何 API provider 不能因为接受本请求而自动获得训练准入权**；正式训练仍受另行控制。

调用成功后，产生一个新的 **0600 私有文件** `R60_REAL_G1_AI_REVIEWS_PRIVATE.jsonl`；原 capture、原空白 reviewer 模板不会被修改或覆盖。文件包含每例两份模型六维评审及私有理由，只保留 Owner Mac。接着用旧程序生成 SAFE：

```bash
python3 experiments/r58_quality/r60_real_private_batch.py \
  review --capture-dir "$RUN" \
  --reviews "$RUN/R60_REAL_G1_AI_REVIEWS_PRIVATE.jsonl"
```

仅将**两条命令的 stdout SAFE JSON**提供给 ChatGPT：模型双审结果计数 / HOLD 原因码，不要发 JSONL 或额外案例标识。若 `R60_REAL_G1_REVIEW_SAFE.json` 已经存在，旧审查器会拒绝覆盖；在这个情况下先使用现存 SAFE，不随意删除或覆盖。

## 重要技术后续

模型不会看到历史完整 System/Story 世界设定。因此六维 `rule_fidelity` 只能评价**局部可见规则**；独立的历史世界一致性和完整世界组件审查仍为 HOLD，不能因模型给出高分就推断世界合规。

所有案例仍需通过：
1. 世界依赖组件 / 独立 Split；
2. **完整** R50 保护集的身份/世界元数据非重合验证（不得读取 R50 正文）；
3. 真实目标前输入构建、避免 future leakage，历史 System 只能显式规范化为 `RECONSTRUCTED_NOT_ACTUAL_SENT`；
4. 真实 Qwen Tokenizer / ms-swift Collator CPU 预检；
5. Owner 单独批准训练批次和付费 HF GPU。

**截止当前回执：G1 真实采集完成 6，双模型评审尚未运行，Quality PASS=0，正式入训 0/0，不动 RolePlay、R50 正文或 Gold192。**
