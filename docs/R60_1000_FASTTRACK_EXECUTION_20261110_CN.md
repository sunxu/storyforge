# R60：已有 1000 条训练候选精筛加速执行书（2026-11-10）

## 2026-11-10 Owner 最新只读 audit：1000 冻结源完整，审核 0/1000

Owner Mac 已实际执行旧双审 adapter 的 `audit`，收到 SAFE：

```json
{"cases_total":1000,"complete_pairs":0,"model_a_reviewed":0,"model_b_reviewed":0,"paid_gpu_submitted":false,"private_values_emitted":false,"quality_decisions":{"HOLD":1000,"PASS":0,"REJECT":0},"quality_pass":0,"quality_v1_admitted":0,"r50_body_accessed":false,"r50_complete_exclusion_verified":false,"reviewer_independence_cryptographically_proven":false,"schema":"storyforge_r60_hf_quality_adapter_safe_v1","status":"HF_QUALITY_DUAL_PARTIAL__NO_ADMISSION","training_authorized":false,"world_isolation_verified":false}
```

**解释：0 完成，1000 HOLD 是未审核状态，不是 1000 条质量不达标。** Frozen 1000 源与旧 stage 的相互验收已通过；当前目标应直接从它们出发，不重新做 Supabase 抽取、不要再次 `prepare`。

### 下一步 Owner Mac：双模型旧审核包纯 CPU 结构预检（不调用模型、不用 GPU）

该命令使用旧 stage 内自带的 `runner.py`，对两个完整 1000-case 输入文件分别执行 `--verify-only`；只读、零收费。**这不能代替 Rubric v2.1 的 30 条准确率校准，也不能授予任何批量 GPU。**

```bash
set -euo pipefail
STAGE="$HOME/.local/share/storyforge/r60/private/r60-hf-quality-first-1000"

for ROLE in A B; do
  case "$ROLE" in
    A) MODEL="Qwen/Qwen3-32B"; REV="9216db5781bf21249d130ec9da846c4624c16137" ;;
    B) MODEL="zai-org/GLM-4-32B-0414"; REV="8dea913c41b543527c2860fb6f3c15c202f24aeb" ;;
  esac
  python "$STAGE/input_$ROLE/runner.py" \
    --input "$STAGE/input_$ROLE/source.private.jsonl" \
    --output-dir "$STAGE/output_$ROLE" \
    --model "$MODEL" --revision "$REV" --verify-only
done
```

预期每侧 `HF_REVIEW_INPUT_VERIFIED__NO_INFERENCE` 且 `cases_total=1000`、`cases_completed=0`。任何 HOLD 保留原始 stage、禁止覆盖。**注意 reviewer v1 基于完整 1000 源的 4 消息结构、可见历史和目标回复，与 R60 30-case v2.1 严重裁决的输出 schema 并不等价。**

### 下一步的正式推理准备

审核端应先把 `S`（Rubric v2.1 严重判定校准）30×3 的模型输入、输出 JSON schema、人工标签隔离和统计门槛验证通过，再启动 A/B 审核者的旧六维质量分批推理。第三模型优先做争议例复核，**不用先运行 1000×3**。旧 `hf_literary_review.py` 虽支持 `--start` / `--limit` 和 1000 条 staged 输入的 checkpoint 断点，但其 GPU 运行函数基于 vLLM，**不能直接将 H200 PyTorch 32K synthetic 的环境和费用视为该 runner 的已验收运行环境**，需另做 vLLM / 资源/预算 CPU-only 静态检查后才会提出单次收费 Job。

---


## 0. 唯一业务目标与当前事实

**目标**：尽快将 Supabase 已粗筛并冻结的约 1000 条真实互动故事历史候选转为经过质量审查、可以用于 StoryForge SFT 的高质量数据；不要扩展为故事生成模型选秀。

已核对同仓库既有工程分支 `r60/gold192-history-v3-adapter`：
- 数据验证入口 `experiments/r58_quality/r60_real_quality_batch.py:frozen_pool`，严格要求 1000 条、扩展页与原始 seed 的 SHA/结构一致；
- 已有审查层 `experiments/r58_quality/r60_hf_quality_adapter.py` 支持 `prepare/audit/export` 三个动作；
- 核心 `src/storyforge_gold_quality/hf_blind_stage.py` 绑定 A/B 各 1000 的独立盲 ID、双模型输出目录和 Owner 本地映射；`audit` **不调用模型**；
- 审核器 `src/storyforge_gold_quality/hf_literary_review.py` 六维：中文文笔、人物一致性、NPC 主动性、玩家自主权、规则遵守、叙事连贯；严重标记：`serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion`；现有质量阈值分别为 4/4/3/4/4/4；
- 既有 staging 根据 Owner 旧回执，位于 `~/.local/share/storyforge/r60/private/r60-hf-quality-first-1000`，冻结 source 扩展目录为同一 private 根下的 `r60-expand-first-600`（以此目录自身配置和文件哈希核验结果为准）；
- 2026-11-08 的已知结果：1000 staged，`model_a_reviewed=0`、`model_b_reviewed=0`、`complete_pairs=0`、`HOLD=1000`、`quality_v1_admitted=0`、`training_authorized=false`。**上述是历史回执，不代表 11 月 10 日实时情况**。
- 当前三模型 32K synthetic GPU 3/3 PASS，不等于审核准确率达标。尤其 B 7 tokens 是被要求输出一句话的 smoke，不应视为审核短输出故障。

### 关键区别

现有 1000 条 pipeline 用 **双模型 A/B 的六维训练质量审核**；R60 **新冻结 Rubric v2.1 + Gold/Owner 30 案例** 用于对三模型严重维度（Hard Rule、Player Agency、Safety）准确率校准。可复用双审工程和 1000 条固定数据，**不可直接声称六维旧 policy 与 v2.1 等价**。第三模型 challenger 优先用于 30 案例校准与冲突复审，不强制让全部 1000 条变成三模型三次全量推理。

## 1. 立即执行的 Owner Mac 本地只读诊断（不收费、无模型调用）

先在 Mac 上使用原 worktree（不要触碰已消费的 H200 三次任务、不要重新 prepare 或覆盖任何 staging）。运行：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge-r60-ledger-diagnostics"
BASE="$HOME/.local/share/storyforge/r60/private"
STAGE="$BASE/r60-hf-quality-first-1000"
EXPAND="$BASE/r60-expand-first-600"
cd "$ROOT"
test -f experiments/r58_quality/r60_hf_quality_adapter.py
test -d "$STAGE" && test -d "$EXPAND"
PYTHONPATH="$ROOT/src" python experiments/r58_quality/r60_hf_quality_adapter.py audit \
  --expand-dir "$EXPAND" \
  --stage-dir "$STAGE"
```

仅粘贴 stdout 的 SAFE JSON，不分享 `owner_crosswalk.private.json`、blind IDs、全文或密钥。如 worktree 不在上述路径，用已有包含 `r60_hf_quality_adapter.py` 的工作区，不改变冻结 staging；若文件不存在则上报 HOLD，不以原始数据库重建 1000 条。

### 预期能确认

- 当前 `cases_total`、`complete_pairs`、A/B reviewed、PASS/HOLD/REJECT、`quality_v1_admitted`；
- 现有 candidate pool 与 stage manifest 有无 SHA 变化；
- 现有 runner 与 Source、model pins 是否仍一致；
- 如果 `complete_pairs>0`，复用既有结果，不重复付费审核。

**注意**：上面当前状态未知，任何结果在返回 SAFE 前只可标记 `CURRENT_1000_AUDIT_PENDING`。

## 2. 30 条 calibration 不得阻塞 1000 条静态检查，但必须阻止“未经校准直接准入”

并行核对 P2-B Locked20 + Severe10 的 30 个已裁决案例，以及 Rubric v2.1 的 Prompt/Schema SHA。三模型严格同案分别审核并冻结预测，再与 Owner 30/90 的明确标签对齐、报告每维误判/漏判/弃判；`INSUFFICIENT_CONTEXT` 只计 HOLD，不能伪造明确标签。**如无结构化三维输出，既有 `generation_eval.worker_cli` 的自由文本输出不得直接当成审核预测**。

30 条校准不要求把历史 1000 条 source 重新获取，亦不要求重新跑三模型 32K synthetic smoke。

## 3. 最快进入 1000 精筛的分批策略

- **第 0 批（CPU-only）**：只读 audit 冻结数据，计算当前真实待审数量、审核器是否已经具备双模型 A/B 分槽 JSON Schema/引用证据校验。复用旧证据，避免重算。
- **校准批**：原样 30 条严格三模型盲审；先 3–5 个 development 结构检查（不能拿 locked labels 做 prompt 调参），再完整 30；结构化结果与新版 Rubric v2.1 对齐。需要收费 Job 时，Owner Mac CLI 提交，固定预算/单次尝试/不自动重试。
- **1000 批处理**：固定 A/B 主审：100 条一组，先 25 条技术 pilot，通过格式、停止、证据引用与成本核验后再扩至 100/500/1000，已完成数不重复计算。严重证据确凿者 REJECT，证据不足或两模型分歧者 HOLD，双 PASS 且六维达标者只进 **可准入候选队列**，需执行 Quality-v1 最终准入 verifier 才能写 `admitted`。Challenger 只审分歧/HOLD（先以 30 条校准证明有价值），避免 1000×3 全量花费。
- **结果导出**：已有适配器只有 `complete_pairs == 1000` 才允许执行 `export`，因此不提前运行；仍由 Owner 控制独立导入 Gold Quality ledger，不改 Frozen 原文或历史标签。

任何用于生产训练的 case 必须满足四消息上下文技术条件、目标回复真实完成、无严重规则/玩家自主权/安全问题及质量阈值；未检验来源时不能自称已审。这份执行书仅调整筛选进度优先级，不改变旧 frozen 样本、旧模型输出或官方 Owner 裁决。

## 4. 明确授权边界

用户 2026-11-10 说「按建议推进，尽快进行 1,000 条候选的精筛」：**现授权推进 1000 条精筛项目的准备与后续实施目标**；不等于批准任何不设上限的收费 GPU Job、自动重试、实际 SFT 训练、修改生产数据库或自动将 HOLD 标记为可训练。

执行类里程碑：
- `1000_FROZEN_AUDIT`：WAIT_OWNER_SAFE。
- `P4_30_THREE_MODEL_CALIBRATION`：准备中，正式模型输出尚无。
- `P6_1000_FINE_SCREEN`：目标获用户明确确认，但本轮实际审核数据 **尚未开始/未得到当前 SAFE 证明**。
- `QUALITY_V1_ADMISSION`：HOLD，不能从双 PASS 自动提升。
- `TRAINING`：未授权。

## 5. 已发现的技术缺口

现存 `hf_literary_review.py` policy 是 `storyforge_hf_literary_visible_history_v1`，不是新冻结的 `r60_severity_rubric_v2_1`。历史 `r60_hf_quality_adapter.py` 仅支持 A/B 两个独立 slot，且 checkpoint/export 依赖旧 runner。下一步只在新 revision 增加 **v2.1 严重问题审核薄适配层**，不要覆盖已准备的 1000 输入或修改旧 checkpoint 语义；新评审只对还没有被审过的批次运行。
