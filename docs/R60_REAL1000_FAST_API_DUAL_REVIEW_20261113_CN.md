# R60 REAL1000 快速筛选执行书：API双审覆盖优先（2026-11-13）

> Owner明示：接受不完美方案，优先尽快推进冻结1000条筛选。本文件是**方案B的快速执行变体**：保留每条A/B审核、证据链及技术HOLD，不再阻塞于HF Qwen3-32B/GLM4-32B工程调试。本文件不代表已有1000条实际模型审核，也不准许将内容/技术HOLD自动入训。

## 选择依据与局限

使用历史已实际验证的 `qwen3.7-flash`（阿里云百炼）+ `deepseek-flash`（官方API）：QD20有效率分别18/20、16/20；不外推为全量有效率或准确率。此二者**不是**原HF Stage固定的`Qwen3-32B`+`GLM-4-32B`，不能将新模型回执写入旧HF Stage或冒充其审稿。与早期Claude+DeepSeek Pilot5也不同，须创建**全新可追溯的私有Quality批次目录**。严禁覆盖原本5份/v2回执。

该方案复用`experiments/r58_quality/r60_real_quality_batch.py`（1000条源验证、最多每次25、不可覆盖case回执、双模型单次请求、错误隔离、inspect SAFE）与`r60_real_ai_dual_review.py`、同一`r60_real_private_batch.FLOORS`。不新建第三Reviewer，不降低门槛。

实际历史 QD20 endpoint/模型名：Qwen `https://dashscope.aliyuncs.com/compatible-mode/v1` + `qwen3.7-flash`；DeepSeek `https://api.deepseek.com` + `deepseek-flash`。须由Owner用现有凭据与当前模型可用性复核；如果响应model和期望不一致或当前服务端协议变更，停机，不能把别名当模型身份证据。

**兼容性注意**：现有私有Quality Batch runner固化 A环境变量 `R60_CLAUDE_KEY`、B `R60_DEEPSEEK_KEY`，虽然模型字段可以是其它模型。为最快复用，不改历史Runner、不改冻结v1：在`advance`单个子进程环境中把`DASHSCOPE_API_KEY`短暂映射给`R60_CLAUDE_KEY`；这是已审查的临时**变量别名**，**不调用Claude**，不在日志打印任何key，也不将凭据写入GitHub或配置。待全量筛选后再做通用变量重构，不在本次阻塞。

## 目标与执行节奏

- 1000条结构PASS、与旧HF Stage身份PASS的Owner SAFE已取得，不重新跑筛选和旧Stage。
- 使用全新 `r60-quality-fast1000-api-v1` 私有目录，`init`只允许一次。
- 第1次只运行25条，明确检验Qwen/DeepSeek**当前**协议/配额和技术失败情况；再在每25条批末汇总SAFE。为了尽快完成，在首批有效且Owner选择继续时可以逐25条推进剩余975，不再以单条文学分歧停止扩批。
- 软异常只记录`MODEL_JSON_INVALID`、分数/严重旗标不一致等技术HOLD，不无限重试。不对轻微分歧额外请求第三模型。
- 硬停：冻结源SHA不一致、配置/回执不一致、输出被覆盖、两服务同时不可用、无效响应明显大面积发生、泄漏密钥/小说正文、费用预算达限。
- 此处“覆盖1000”表示`cases_reviewed=1000`、每例有A/B尝试及不可覆盖回执；不意味着`complete_pairs=1000`，更不意味着`quality_pass=1000`。
- 不使用`--owner-attest-independent-ai`，除非Owner实际完成各模型独立性核对；因此正式Quality PASS可能保持0，报告须另区分双审有效且双方PASS的临时候选和最终准入。

## Owner Mac 命令（先25条）

~~~bash
set -euo pipefail
set +x
umask 077
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
test "$(git branch --show-current)" = "r60/common2-cpu2-owner"
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
SOURCE="$BASE/r60-expand-first-600"
OUT="$BASE/r60-quality-fast1000-api-v1"
: "${DASHSCOPE_API_KEY:?在当前私有终端预先设置Qwen API key}"
: "${DEEPSEEK_API_KEY:?在当前私有终端预先设置DeepSeek API key}"
test ! -e "$OUT"

"$PY" experiments/r58_quality/r60_real_quality_batch.py init \
  --expand-dir "$SOURCE" --output-dir "$OUT" \
  --endpoint-a "https://dashscope.aliyuncs.com/compatible-mode/v1" \
  --model-a "qwen3.7-flash" --protocol-a openai-chat \
  --endpoint-b "https://api.deepseek.com" \
  --model-b "deepseek-flash" --protocol-b deepseek-chat \
  --allow-remote-review --timeout 180

R60_CLAUDE_KEY="$DASHSCOPE_API_KEY" \
R60_DEEPSEEK_KEY="$DEEPSEEK_API_KEY" \
"$PY" experiments/r58_quality/r60_real_quality_batch.py advance \
  --output-dir "$OUT" --max-cases 25

"$PY" experiments/r58_quality/r60_real_quality_batch.py inspect \
  --output-dir "$OUT"
~~~

注意：`init`不检查凭据也不会发送私有正文；`advance`才会对外发送模型审核提示。现有`advance`是串行按案例调用两个API，对现有目录无需重新init。不要对旧`r60-quality-first-1000`运行此快速筛选配置。当前用户选择加速方案，但实际API用量/费用仍需Owner在运行时控制；外发范围为全量1000条可见3消息+目标正文（每例A/B各一次）。

## 首25验收，然后批量覆盖

首25的`inspect`必须返回`cases_reviewed=25`，模型请求错误不能全部被判为文学REJECT。预设工程止损（用于防灾，不是质量门槛）：25条中模型技术失败总数**超过20个槽位**就暂停、定位协议；如果两个provider同一案例都出现网络/服务级不可用，原Runner会在写该案前HOLD，原样保留可恢复进度。其它文学REJECT/HOLD不触发暂停。

确认首25正常且预算允许后，逐批推进。为避免40次手动操作，下面可选择在Owner Mac**前台**执行、保留每批SAFE并在任何返回非零时停止；不启动后台任务。

~~~bash
# 在上面的变量和API key仍在同一终端时使用；仅当首25已验收
for round in $(seq 2 40); do
  R60_CLAUDE_KEY="$DASHSCOPE_API_KEY" \
  R60_DEEPSEEK_KEY="$DEEPSEEK_API_KEY" \
    "$PY" experiments/r58_quality/r60_real_quality_batch.py advance \
      --output-dir "$OUT" --max-cases 25
  "$PY" experiments/r58_quality/r60_real_quality_batch.py inspect \
    --output-dir "$OUT"
done
~~~

该前台循环尚**没有内建**成本上限、技术HOLD占比自动停机或完整自动成本计算。因此不应在无人监管时使用；如需要全自动、成本硬上限，应单独增加守卫而非绕过现有回执不可覆盖保障。遇临时错误可停止并反馈SAFE，不删目录、不覆盖v1结果。

## 完成后的通用统计

已有`inspect`提供`candidate_total`、`cases_reviewed`、`quality_decisions`、`hold_reject_codes`、`model_attempt_hold_counts`。由于未自动认可Reviewer独立性，`quality_pass`不代表预备双PASS总量；任何进一步“提取训练候选”须从Owner-only回执读取并按原冻结六维/严重标记及精确证据核验后，在新的私有候选集单独汇总，**不得篡改已有回执或自动Gold晋升**。

当前保持`quality_v1_admitted=0`、`train_admitted=0`、`gpu_started=false`、`r50_complete_exclusion_verified=false`、`historical_system_snapshot_verified=false`、`world_isolation_verified=false`。
