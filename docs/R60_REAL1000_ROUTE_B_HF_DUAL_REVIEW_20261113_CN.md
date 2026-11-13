# StoryForge R60 REAL1000：方案 B 冻结执行书（2026-11-13）

> Owner 于2026-11-13明确选择 **方案 B：直接对现有1000条 HF A/B Stage进行独立双审，之后按需仲裁**。这**不是**提交收费HF GPU/CPU Job、上传私有数据、Gold事件写入或训练的授权。严禁复用Pilot5-v1/v2本地Claude/DeepSeek回执冒充HF Reviewer结果。

## 1. 已通过的事实门禁

- 冻结来源1000/1000、离线结构预筛1000 PASS、EXCLUDE0、CONTEXT_HOLD0。
- Owner真实`PREFILTER_STAGE_ALL_ELIGIBLE__CONTENT_REVIEW_PENDING`；1000/1000 预筛身份与现有 A/B HF Stage逐条匹配。
- Owner真实 HF adapter `audit`为A/B已有有效审核0/0、`complete_pairs=0`、全部1000“待审核”HOLD；并**非**1000质量拒收。
- 原Stage两个Reviewer固定在owner-only manifest，历史登记是 A `Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137`、B `zai-org/GLM-4-32B-0414@077b5c2f5c43bd3239fd605a0600229e8facbd4a`；**运行前必须由既有manifest再次验证，不能用文字里的历史pin代替当前私有绑定**。
- 原`hf_blind_stage.verified_stage` 验 source/两份input/模型runner/tokenizer/Owner跨表的SHA，`r60_hf_quality_adapter.py audit` 做只读进度；原`hf_literary_review.py` 具有`--start/--limit`、create-only checkpoint、SHA/逐字引用复验、截断FAIL及同组已完成跳过能力。
- 当前旧HF CPU说明中本地 `-v 本地input` 会隐式上传到 jobs-artifacts；不得使用。仅在独立授权后显式推送至组织 `adradar/storyforge-training` 私有 Bucket，A/B只读输入与RW输出互不交叉，Owner Crosswalk始终留在Mac。
- `scripts/hf_job_guard.py` **明确只支持CPU**，不可把它伪装为审核GPU授权器；HF GPU必须先另立经验证的执行/隐私/费用门禁，不能通过绕过CPU Guard直接提交。

## 2. 正式选择的流程

1. **已有1000条作为审阅母集**，不再重复语义前筛，不创建新Stage、不删除任何数据。
2. 对A/B在**各自独立盲审顺序**运行每次至多5个起始样本的首批GPU评估（建议起步`--start 1 --limit 5`，但需先审查是否跨足够故事、对两路真实checkpoint的约束）；此批仅验证完整输出、准确引用、严重标记和运维可靠性，不用Pilot5局部质量率推断1000总体。
3. 仅在Owner验收首批 **两个槽位都有效的checkpoint和审阅内容**、结果无模型协议/技术失败，且单位成本/隐私审计允许后，再计划按25～100每段持续覆盖所有1000。**A/B各自shuffle盲顺序，不可以拿A的前5与B的前5视为同5案配对**；每段要以Owner Crosswalk做来源集合配对、计算真实完成对数，不能按序号假合并。
4. 某一Reviewer结果无效时记`TECHNICAL_HOLD`，保留生成快照/原状态，不擅自改评分、严重标记或原因。失败模型/状态不能算文学REJECT。
5. A/B有效意见对同一源绑定之后，六维最低分`4/4/3/4/4/4`及严重标志的硬约束保持；双审冲突、严重问题、引用不足、未知世界卡/System仅触发**来源证据仲裁**，不能靠投票或第3个通用评分模型强行合并。故事原文/逐案ID/审阅理由不写公共Github。
6. 完整1000×2 的有效审稿/准入的`hf_blind_stage.export_pipeline_reviews`只能在既有私有 Manifest需要的完整门禁满足后进行。先导出独立Reviewer A/B事件，检查来源、SHA及Owner独立性，然后才有Gold Manifest的**单独写入授权**；Gold和SFT训练均另验。

## 3. 先不花钱的Mac只读核验

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
"$PY" experiments/r58_quality/r60_real1000_prefilter_stage_crosswalk.py \
  --expand-dir "$BASE/r60-expand-first-600" \
  --prefilter-dir "$BASE/r60-real1000-prefilter-v1" \
  --stage-dir "$BASE/r60-hf-quality-first-1000"
"$PY" experiments/r58_quality/r60_hf_quality_adapter.py audit \
  --expand-dir "$BASE/r60-expand-first-600" \
  --stage-dir "$BASE/r60-hf-quality-first-1000"
~~~

已有SAFE确认首条通过，**不需要为取新证据而反复运行**。此处命令是单一公开入口，后续只需有改变时重验。

### 必须另外满足的运行准备

- A/B模型revision、镜像digest、Linux vLLM/transformers兼容、显存与资源上限、HF推理成本上限：运行前冻结，不使用未经验证的`vllm/vllm-openai:v0.11.0`示意镜像直接上生产。
- A/B各自`token_preflight`需有针对1000条实际输入的CPU回执，并确认`cases_checked=1000`、`over_budget_count=0`、与Stage code SHA/model pin一致。Common2 2条CPU Collator PASS**不能替代**这条1000输入HF Reviewer CPU预检。
- 仅使用受控组织项目Bucket，`/input` RO、`/output` RW，既有Owner-only crosswalk不上传HF；没有用户批准不发起上传或HF Job。
- 双reviewer的真实训练独立性无法从“两个不同模型名称”密码学证明；审稿数据可记录`INDEPENDENCE_UNVERIFIED`，不得自动当作高质量Gold PASS。
- 首批通过后运行`r60_hf_quality_adapter.py audit`，SAFE需分开报告A=有效数量、B=有效数量、真实同案`complete_pairs`、技术HOLD原因；如果A/B各自随机前5不重合则`complete_pairs=0`是**正常而非任务失败**，不得补造为5。

## 4. 首批停止条件和授权点

**任何一个出现就暂停下一次请求**：源/Stage/代码SHA不符、未验证1000 token预算、输出越界/公开隐私、同模型重复而未记状态、无效JSON/引文不精确、模型score/decision与严重标记冲突、checkpoint失败、HF兼容/费用上限不明、A/B引用模型revision不符。

本方案B表示“选定质量评审路线”；在执行第一份真实HF模型推理前，Owner还需确认**可使用的付费计算资源、首批请求/最大时长与单轮费用上限、私有数据对HF组织Bucket的可出域许可**。授权的范围不自动扩展到1000×2、训练或Gold。

## 5. 工程增量与边界

本阶段不修改`hf_blind_stage.py`、`hf_literary_review.py`或冻结1000数据，不重写独立审稿/Validator。若将来需要自动调度或抽样，先编写只读的checkpoint进度/成本计划和合成测试；未经批准不实现能自动提交HF收费任务的新触发器。

**下一步执行命令：先核实1000条HF Reviewer CPU Tokenizer预检是否曾取得完整实际SAFE。如无，则使用旧 CPU Guard进行不提交的dry-run（见 `docs/R60_HF_QUALITY_CPU_PREFLIGHT_AFTER_STAGE_20261108_CN.md`）。GPU工作仍停留在授权门禁之前。**
