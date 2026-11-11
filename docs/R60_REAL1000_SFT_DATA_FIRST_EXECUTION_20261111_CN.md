# StoryForge R60 — 真实1000条优质历史数据 → SFT 数据优先执行任务书（2026-11-11）

## 2026-11-11 Owner P0 真实验收完成（覆盖下文 P0 待执行的历史说明）

Owner Mac 已对冻结 `r60-expand-first-600` 执行原生 `inspect` 与新 CPU 画像，真实 SAFE：
- 合成单测 `6 passed in 0.04s`；
- `EXPANSION_TARGET_REACHED__NOT_ADMITTED`，6种子 +994扩容=1000、20页、扫描400故事；
- `REAL1000_TECHNICAL_PROFILE_PASS__QUALITY_PENDING`，`cases_verified=1000`、`distinct_stories=285`、`max_cases_per_story=4`、三消息链和持久化目标各1000；
- 目标回复长度分布：300–499字545条、500–999字380条、1000–1500字75条；
- 历史实际System、世界组件、R50排除均有1000条状态未核证；这是后续训练前证据项，不应重新当成质量审核硬阻塞；
- `quality_review_performed=false`、`quality_pass=0`、`train_admitted=0`，无数据库访问或 GPU。

**因此 P0=PASS，下一项直接开始 P1质量校准抽样，不再重拉DB或 Tokenizer。**

新增 `r60_real1000_calibration_sample_cpu.py`：调用既有 `frozen_pool` 重新只读验签后，从1000条中按冻结池指纹+case_key确定性选100条，长度层配额55（300–499）/38（500–999）/7（1000–1500），每故事仅1条；只在Owner Mac新私有0700目录保存原始位置+长度层，不复制或公开原文/故事ID，公开输出仅SAFE计数。若任一配额无法满足故事唯一性则HOLD，不降低配额或自动覆盖历史抽样。

Owner Mac 下一命令（仅 CPU、无模型审核调用）：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BRANCH="r60/p4-generation-eval-framework"
BASE="$HOME/.local/share/storyforge/r60/private"
EXPAND="$BASE/r60-expand-first-600"
SAMPLE="$BASE/r60-real1000-calibration100-v1"
git -C "$ROOT" fetch origin "$BRANCH"
PIN="$(git -C "$ROOT" rev-parse "origin/$BRANCH")"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/r60-calibration100-XXXXXX")"
git -C "$ROOT" worktree add --detach "$WORK" "$PIN"
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_calibration_sample_cpu.py
test ! -e "$SAMPLE"
python3 experiments/r58_quality/r60_real1000_calibration_sample_cpu.py \
  --expand-dir "$EXPAND" --output-dir "$SAMPLE"
```

预期 `CALIBRATION_SAMPLE100_READY__NO_REVIEWS`，`sampled_cases=100`，`distinct_stories=100`，层配额55/38/7。**这只是可重复的独立抽样，不是100条质量已经 PASS。**


> **当前优先级入口；替代同日 GLM/Qwen 全量调试继续扩大的待办。** 单 Agent 负责 `r60/p4-generation-eval-framework`。本任务书只授权 GitHub 代码/文档、CPU-only 只读诊断；**不授权新的远端付费任务、GPU 推理、训练、数据库更改、PR 合并或正式训练准入**。

## 1. 目标与当前事实

目标是把已冻结的真实互动小说历史候选，尽早转换为经可证伪质量筛选的**首批训练候选**，继而做世界/历史/评测隔离、CPU Tokenizer/Collator、训练前审查。禁止以完成 GLM/Qwen 排障作为数据准备的前置条件。

已获得的历史 Owner SAFE：`EXPANSION_TARGET_REACHED__NOT_ADMITTED`，6条种子 + 994条新候选 = **准确1000条**；共20页、扫描400个故事。候选已保存在 Owner Mac `$HOME/.local/share/storyforge/r60/private/r60-expand-first-600`，采集输入为每案目标前3条实际 DB 消息（user/assistant/user）+ assistant 目标；不是完整多轮历史或实际发送的系统提示词。阶段性结构筛选条件为原始 `r60_real_expand_private.py` SQL 的**已完成 assistant、有效邻接角色链、目标长度300–1500、前序 user/assistant 长度边界、无已标记编辑或解析告警、非分叉根会话、每世界不超过4候选**等；这是**采集技术预筛**，并不证明高质量、长上下文完整、真实 System、世界卡或入训资格。

既有 A/B 各1000/1000的 CPU tokenizer 预检及 Owner crosswalk 验证已做；**不重新下载/导出、采样、CPU tokenizer，除非输入配置本身改变**。现有 `r60_real_quality_batch.frozen_pool` 可用原始页/seed、SHA、重复项、结构、Prompt 边界严格只读验证整池。既有 `r60_hf_quality_adapter.py prepare` 已在 Owner 实测1000 staged，`audit` 显示双模型审核0/1000，不能冒称已经审核完毕。

工程对照：GLM 全25份 Snapshot + CPU Replay 完成，模型原始25个 `decision=REJECT`；不是人工真值，剩余8个引用失败与质量区分。Qwen 前6份验签，第7条异常；在得到样本准入增益证据前，不继续为两者付费。GLM/Qwen 已有工程资产保留，不丢弃。

## 2. 立即执行：Owner 冻结池 CPU 状态检查（零 GPU）

使用当前单 Agent 分支的固定 HEAD + 既有工具检查（不改变原20页或种子，不重新访问数据库）：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
EXPAND="$BASE/r60-expand-first-600"
PIN="$(git -C "$ROOT" rev-parse origin/r60/p4-generation-eval-framework)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/r60-real1000-cpu-XXXXXX")"
git -C "$ROOT" worktree add --detach "$WORK" "$PIN"
cd "$WORK"
python3 experiments/r58_quality/r60_real_expand_private.py inspect --output-dir "$EXPAND"
python3 experiments/r58_quality/r60_real1000_technical_profile_cpu.py --expand-dir "$EXPAND"
```

只有当 `EXPANSION_TARGET_REACHED__NOT_ADMITTED` 且新 `REAL1000_TECHNICAL_PROFILE_PASS__QUALITY_PENDING`、`cases_verified=1000` 均收到，才视为**冻结候选池技术结构已核验**。若旧实际私有目录已迁移，Owner 用真实目录代入，不通过复制/覆盖原页伪造修复。脚本 SAFE 只显示结构性计数，无正文、ID、哈希，不生成正式准入标签。

## 3. 质量校准：先分层100条，不重启三模型批量

从技术核验通过的1000条中，在 Owner 私有工作区构造**故事分层、长度/复杂度分层的约100条校准子集**。与已冻结 Gold72 的 Development 部分和 Owner v2.1 Rubric 可对齐的才作为校准参考，Locked20、Severe10、R50 保留为评测/回归，不向待校准模型暴露答案。*不能直接把不同来源的 Gold 标签按“第n条”位置匹配这1000条；先用 Owner crosswalk/来源严格匹配，确无匹配则独立新裁决。*

质量判定核心：中文文笔、人物一致、NPC主动性、玩家自主权、局部规则/事实、叙事连续性。严重项必须有**明确支持的语义证据**；引文格式失败与质量不合格独立记录。用已经可用的单主模型/API 对校准样本评分，抽查误拒/漏拒；无法验证严重标记时 HOLD，不直接批量淘汰。若已有 Owner/人工参考，优先复用；不因为某模型25条全部 REJECT 就推断所有候选不合格。

**校准停止条件**：100条抽样内没有经过独立参考验证的稳定误判指标时，不扩大至1000条全量模型审核；改为受控 Owner 案例复核/简化审核合同。不要重复升级 Reviewer 框架来代替判断。

## 4. 第一批训练候选（先50–100，不等待1000条全部完审）

只从达到质量准入评审条件的实例中生成 `TRAIN_CANDIDATES_PRIVATE`（不是 TRAIN_ADMITTED），保留输入页指纹、来源与目标前历史链、原始回复 SHA、审核版本/证据以及拒绝/HOLD 的独立原因。来源 ID 与目标摘要仅用于技术追溯、去重和历史链关联；本轮按 Owner 已明确简化的审核范围，**不把来源权利、隐私、授权证据作为质量评审前置项**。Gold192、R50、Locked regression 等冻结评测集继续保持独立，避免数据泄漏到测试。

世界组件与历史 System 未完整核证的样本，**只能进入技术准备/质量候选，不能直接宣称训练准入**。在 CPU 上完成真实世界切分、Prompt 重建策略、Target 归属、去重、Tokenizer 和 Collator 验证后生成 SAFE 候选计数；训练数据冻结和 SFT GPU 另行授权。

## 5. 阶段闸门及单一事实来源

| 优先级 | 任务 | 完成的真实证据 |
|---|---|---|
| P0 | 冻结1000条只读核验 + 技术画像 | 官方 expand inspect PASS；全1000结构验证 PASS；质量状态仍独立 |
| P1 | 100条分层校准与独立误拒/漏拒评价 | 抽样覆盖、独立参考、Rubric对齐的 SAFE 汇总 |
| P2 | 首批50–100高质量训练候选 | 逐条质量判定与可追溯来源、未覆盖旧数据 |
| P3 | 训练格式/切分/Tokenizer/Collator | CPU 验收报告 |
| P4 | 单独批准训练数据准入/下一次 SFT | Owner 授权及训练预算 |

**明确暂停**：GLM 同25的再次H200、剩余8引文修复、Qwen第7条追加H200、三模型30条配对测试的扩大、1000条双模型GPU强制全覆盖、重复源池导出、重复 Tokenizer/Model Runtime Smoke。只有被证明是 P0–P3 数据交付的真实阻塞，才升级到对应工程任务，并单独批准费用。

## 6. 保留的限制与尚未完成事项

- 1000条采集成功 ≠ 本轮1000条技术画像已重跑 ≠ 质量PASS ≠ 训练准入。
- 旧记录包含 `quality_v1_admitted=0`，不能把首批 TRAIN_CANDIDATES 当作已批准训练。
- 不把3条前文称作完整故事上下文；不虚构当时真实 System。
- 不修改 RolePlay，不合并 PR #30，不上传私有正文/ID/哈希/交叉映射至 GitHub。
- 本次代码创建和 CI PASS 只证明合成代码，无 Owner 私有1000条现场 SAFE 时技术画像仍 HOLD。
