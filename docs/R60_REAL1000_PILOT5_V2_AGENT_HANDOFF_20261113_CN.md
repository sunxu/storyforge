# StoryForge R60 REAL1000 / Pilot5-v2 新 Agent 接手任务书

> **补充诊断（2026-11-13，Owner Mac 固定错误码聚合）**：已记录的 v2 三次请求结果为 `SUCCESS=1`、`QUALITY_FLOOR_DECISION_INCONSISTENT=1`、`SEVERE_FLAG_DECISION_INCONSISTENT=1`。已核对 `r60_real_ai_dual_review.parse_model_response`：前者精确表示 Reviewer 声明 `decision=PASS`，但至少一项六维分数低于冻结最低分；后者精确表示至少一个严重标记为 `true`，但 `decision!=REJECT`。两个失败均是**决策与分数/严重标记合同不一致**，不是已证实的传输或 JSON 语法失败。当前冻结下限为 `chinese_prose=4,character_consistency=4,npc_initiative=3,player_agency=4,rule_fidelity=4,narrative_continuity=4`，严标为 `serious_player_agency,hard_fact_or_ban,safety_exclusion`。公开 SAFE 不绑定具体失败侧、原始分数或严重标记明细，不能推断是哪一槽位、分数是多少或哪项标记为真。**不修正模型决定、不降低阈值、不覆盖任何 v2 HOLD，不重跑 Reviewer。** 后续独立语义判断需要 Owner 私有证据的单独只读路径；仅凭聚合 SAFE 无法形成逐案裁决。Pilot25、Gold准入与训练持续 HOLD。


> **最新执行结果（2026-11-13 Owner Mac SAFE，覆盖下方旧阶段说明）**：Owner 已明确授权且通过现有定向执行器完成全部3个模型请求；返回 `PILOT5_V2_REPLAY_ATTEMPTS_SAVED__NO_PROMOTION`（`model_requests=3`、`successes=1`、`attempt_holds=2`、`already_recorded_slots=0`）。随后只读 crosswalk 返回 `PILOT5_V2_CROSSWALK_INTEGRITY_PASS__QUALITY_HOLD`（`v1_cases=5`、`v1_valid_reviews=7`、`v2_recorded=3`、`v2_success=1`、`v2_attempt_holds=2`、`unresolved_slots=2`）。3份 v2 回执均已记录且不可覆盖；**只有1份新增有效审核意见，总有效意见8份**，另外2份是技术失败，不是文学REJECT或有效质量HOLD评分。SAFE 不揭示具体成功/失败侧与失败原因，不能猜测。**停止此 v2 命名空间任何自动重跑、删改或同计划重试**；后续只能做只读证据核验与已有8份意见的局部语义复核。技术失败是否另立 v3 纠错须先做私有失败原因/请求边界调查、单独版本化方案与Owner再次授权。#2/#3/#4/#5 未完成独立语义裁决，Pilot25/Gold/训练全部 HOLD；`train_admitted=0`，未写DB、未启GPU/HF Jobs。


> **2026-11-13 Owner Mac 新 SAFE（优先于下文历史状态）**：Owner 已回传执行器真实无网络预检 `PILOT5_V2_REPLAY_PREFLIGHT_PASS__NO_REQUEST`：`planned_slots=3`、`already_recorded_slots=0`、`model_requests=0`、`train_admitted=0`、`database_modified=false`、`gpu_started=false`。当前不再等待预检，下一门禁是 Owner 对 #1-B/#3-A/#3-B 三个真实模型调用的单独明确批准。新增独立 `r60_pilot5_v2_crosswalk.py` 复用既有 verify / verify_existing_slot 做只读 v1/v2 完整性核查；在未补审时输出 `PILOT5_V2_CROSSWALK_PARTIAL__QUALITY_HOLD`，不能升级 Gold。HF CPU、GPU、训练、DB、R50正文与剩余995均不执行。


> 状态基准：2026-11-13；仅针对隔离 Owner 分支 `r60/common2-cpu2-owner`。新 Agent 必须重新核实 GitHub 当前 HEAD / Actions / 已冻结 Mac SAFE 回执，不能用本文件推定未来状态。

## 1. 本轮目标与执行权

本轮目标是**补齐 Pilot5 原有3个技术失败槽位的有效审核证据、独立裁决真实质量分歧、形成是否值得扩批25条的决策依据**，而不是让1000条直接入训。先在 Owner Mac 执行离线预检，确认已有的 v2 私有计划、v1 回执和冻结池身份没有变化；任何真实API补审必须由 Owner 显式批准并仅在 Mac CLI 执行。Agent 可以维护共享代码、回归测试、文档、GitHub CI 和 SAFE 结果分析；不要通过 ChatGPT/HF 插件代替Owner提交Jobs。不得读取R50正文，不得写数据库，不得自动训练/GPU，不得重启旧HF任务。

仓库：`https://github.com/sunxu/storyforge`。
- Owner工作分支：`r60/common2-cpu2-owner`（与其他 Agent 分支隔离；不要直接合并/重置/强推其他人的工作）。
- Owner Mac worktree：`~/workspace/storyforge-r60-4router-review`。
- Mac Python：`$HOME/.local/share/storyforge/venvs/r60-owner/bin/python`。
- Owner私有根：`$HOME/.local/share/storyforge/r60/private/`，所有私有文件/回执只留Owner设备，目录0700、文件0600。
- 相关 Issue：[#26](https://github.com/sunxu/storyforge/issues/26)。其他 R60 Agent 可能同时修改主线，任何推送前再次拉取与校验当前分支。

## 2. 已完成的可验证事实

1. 冻结 REAL1000 候选池：Seed6 + 新994，共1000，尚未质量/训练准入。候选池 `EXPANSION_TARGET_REACHED__NOT_ADMITTED` 为先前 Owner SAFE 状态。
2. Claude Opus 5.5/4Router（A，`claude-proxy-top-system`）及官方 DeepSeek Flash（B，`deepseek-chat`）各有合成端点 `REVIEWER_SYNTHETIC_API_PASS__NO_PRIVATE`；无需反复合成探针。历史 Claude 成功协议已复用顶层system、max_tokens12000、text-block/finish_reason 兼容，且共享严格六维校验。
3. Pilot5-v1 实际5案回执、Seed6原件由Owner提供并核验：来源绑定5/5 PASS；独立只读Owner Mac `PILOT5_V2_EVIDENCE_INTEGRITY_PASS__NO_PROMOTION`。逐案最终 HOLD3 / REJECT2 / PASS0；已保存的7份有效 Reviewer 意见为 HOLD3 / PASS1 / REJECT3；另有3个技术失败。
4. 已生成独立 create-only v2 计划，Owner Mac SAFE：`PILOT5_V2_REPLAY_PLAN_PREPARED__NO_REQUEST`，`failed_slots=3`，`planned_positions=2`，`model_requests=0`，`train_admitted=0`。**计划已存在，禁止重新创建/删除目录。**
5. 新定向执行器 `experiments/r58_quality/r60_pilot5_v2_replay_execute.py` 默认无网络预检，显式双参数才允许外发。GitHub Actions [#43337488525](https://github.com/sunxu/storyforge/actions/runs/43337488525)：Ruff PASS、**pytest 63/63 PASS**；这是合成 CI，不是 Owner 私有实测补审成功。
6. 到本任务书创建时，**尚无 Owner Mac 的 `PILOT5_V2_REPLAY_PREFLIGHT_PASS__NO_REQUEST` 回执**，也尚无真实 v2 模型补审结果。这是下一步，不能把 CI 或计划生成 PASS 冒称成真实补审 PASS。
7. 全程 `database_modified=false`、`gpu_started=false`、`train_admitted=0`；世界隔离、R50完整排除、历史System确切快照、Owner模型独立性验证均没有完成，不可伪造这些门禁。

## 3. v1五案例与严格补审边界

| 位置 | v1 A: Claude | v1 B: DeepSeek | v1 总决策 | v2 允许新模型请求 |
| --- | --- | --- | --- | --- |
| #1 | HOLD有效 | `QUALITY_FLOOR_DECISION_INCONSISTENT`技术拒收 | HOLD | **只补 B** |
| #2 | REJECT + severe player agency | HOLD有效 | REJECT | **不重跑**，独立语义裁决 |
| #3 | `MODEL_JSON_INVALID` | `MODEL_JSON_INVALID` | HOLD | **只补 A+B** |
| #4 | PASS有效 | HOLD有效 | HOLD | **不重跑**，独立语义裁决 |
| #5 | REJECT有效 | REJECT有效 | REJECT | **不重跑**，独立语义裁决 |

唯一允许的失败槽位是 `(1,b),(3,a),(3,b)`，顺序固定。原7份有效 Reviewer 的任何 PASS、HOLD、REJECT 都不是“技术失败”，**不得以分歧为理由重跑**。保存每次新v2私有回执，原v1回执、源池和计划均不可覆盖。任何已写入的v2失败HOLD也是不可覆盖记录，不因网络不稳定而绕过去重重试；需要新一代版本、身份核验和明确批准。

质量独立复核提醒：
- #2：玩家明示要离开，却被NPC在文中抓腕/围困；需按冻结严重玩家能动性 Rubric 判断“阻止离开”的程度，不简单采纳A/B票数。
- #3：即使技术输出恢复，也有 NPC 代写玩家后续对话、进食和移动的风险；质量结论独立进行。
- #4：NPC声称玩家曾答应分配时间，三消息无法证实；区分 NPC 不可靠说辞和叙述给玩家捏造事实。
- #5：双REJECT且均有 `safety_exclusion=true`，另一方有严重玩家代理争议。不要从制服单一线索断定角色实际年龄；不得将其作为正面训练Gold。
- #1：“爸爸”等称谓与真实关系、玩家年龄无已核实世界卡/历史System证据；不要自行补设定。

六维质量分数门槛（冻结）：`character_consistency=4`、`narrative_continuity=4`、`rule_fidelity=3`、`player_agency=4`、`npc_initiative=4`、`chinese_prose=4`；严重标记 `hard_fact_or_ban` / `serious_player_agency` / `safety_exclusion`。现有审核器不保证逐字证据引用，独立语义结案不得凭“模型返回合法JSON”就放行Gold。

## 4. 下一步 P0：Owner Mac 离线预检

只运行以下命令，不加任何执行/外发参数：

```bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner

PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"

"$PY" experiments/r58_quality/r60_pilot5_v2_replay_execute.py \
  --quality-dir "$BASE/r60-quality-first-1000" \
  --output-dir "$BASE/r60-pilot5-v2-replay"
```

预期SAFE：`PILOT5_V2_REPLAY_PREFLIGHT_PASS__NO_REQUEST`，`planned_slots=3`，初始 `already_recorded_slots=0`，`model_requests=0`。若收到HOLD，禁止自行重置v1/v2或强行请求API；先依据源码、SAFE回执和已有私有文件权限定位，修复必须有合成测试与GitHub CI。若Agent无法访问Owner Mac，提供命令并请Owner回传SAFE；不要声称已执行。

## 5. P1：如 Owner 明确授权，再执行最多3次失败侧补审

默认命令**不**外发。真正发起请求必须同时加 `--execute --allow-private-data-egress` 并且相关环境变量存在：`R60_CLAUDE_KEY`、`R60_DEEPSEEK_KEY`（严禁回显）；配置模型/URL来自冻结v1 config而非命令行临时变更。执行器支持 `--max-requests 1..3`；首次应先对预算/网络/返回保存机制进行风险确认。示例仅供Owner批准后使用：

```bash
"$PY" experiments/r58_quality/r60_pilot5_v2_replay_execute.py \
  --quality-dir "$BASE/r60-quality-first-1000" \
  --output-dir "$BASE/r60-pilot5-v2-replay" \
  --execute --allow-private-data-egress --max-requests 3
```

执行器对每个未完成槽位create-only写 `R60_PILOT5_V2_REPLAY_SLOT_<position>_<SIDE>_PRIVATE.json`（0600）。读取已保存回执以判定成功/失败，`HOLD`和`SUCCESS`均不允许覆盖。实现的失败边界：如果远端请求发生不可捕获异常、进程中断或未能保存结果，可能产生“API已发出但无回执”的不确定状态；**禁止未经核实直接再次执行**，先核对私有目录/请求账单与日志并形成独立异常裁决。

执行结果**不自动合并回v1、不自动改质量决策、不准入训练**。之后必须开发/验证只读 v1+v2 crosswalk（按原始 SHA/侧别、缺失槽位、schema、完整六维、严重标记绑定），另外进行#2/#4/#5和#3的语义裁决，再给出是否扩批25的明确Owner决策；在此前剩余995条不推进。

## 6. 严格禁止与并行协作

- 禁止重建既存 v2 plan、删除回执绕过去重、覆盖原 Pilot5-v1、修改冻结池、将模型格式失败记作文学REJECT、将双模型结果当作自动Gold。
- 禁止无独立批准批量扩展25或995条、训练/GPU、提交HF Jobs、写Supabase/数据库、读取R50正文。
- 禁止提交私有候选、原文、A/B理由、API密钥、完整请求或鉴权响应到GitHub、Issue或公开SAFE输出；公开报告只含固定SAFE码和聚合计数。
- 用户另有并行 Agent 推进其他R60（特别是 Qwen/GLM/HF），只在Owner隔离分支修改本工作流文件；推送前核对冲突，提交清楚的代码、测试、文档和Actions链接。
- Owner的API私有外发授权已用于本轮审核，但每个新执行动作依然要满足代码双开关和明确批准；不可把“已建计划”解释成“已执行请求”。

## 7. 文档权威性与交付验收

依次核对：
1. 本文件（当前阶段快速交接）及 `docs/R60_REAL1000_PILOT5_START_20261112_CN.md`（运行手册，旧章节是历史，不应反向覆盖最新状态）。
2. `docs/standards/GOLD_QUALITY_PIPELINE_CN.md`（冻结质量与入训门禁）。
3. `skills/storyforge-real-quality-review/SKILL.md`（Reviewer协议、独立性和保密规则）。
4. `experiments/r58_quality/r60_pilot5_v2_replay_plan.py`、`r60_pilot5_v2_replay_execute.py`、`r60_pilot5_v2_safe_audit.py`及同名test。
5. `.github/workflows/r60-real1000-quality-review.yml`；[Actions #43337488525](https://github.com/sunxu/storyforge/actions/runs/43337488525) 为已验证基线，不代表未来更改通过。

新Agent需交付：实际Owner Mac预检SAFE、失败槽位执行与逐侧私有回执状态（如已获批准）、v1/v2只读配对核验、#2/#3/#4/#5独立语义证据裁决、CI通过链接、更新手册及Issue #26、明确继续/HOLD决策。未完成部分必须标记为未完成，不得靠推测补齐。

## 8. 新Agent启动提示词

请将下列提示直接用于新对话；以GitHub实时HEAD和Owner Mac实际SAFE为准，禁止仅按本提示词宣称已执行。 

> 你现在接手 `sunxu/storyforge` 的 **R60 REAL1000 Pilot5-v2 定向补审与质量裁决**。先完整阅读本文件、运行手册、GOLD_QUALITY_PIPELINE_CN.md、Reviewer Skill，核对隔离Owner分支 `r60/common2-cpu2-owner` 当前HEAD、Issue #26、GitHub Actions。已知5案v1来源与回执完整性 PASS，计划 `PILOT5_V2_REPLAY_PLAN_PREPARED__NO_REQUEST`（失败槽位#1-B/#3-A/#3-B共3次；已有效7份不得重跑），定向执行器CI Ruff+63/63 PASS。**尚未收到Owner Mac执行器预检或真实v2补审SAFE。** 先让Owner在 `~/workspace/storyforge-r60-4router-review` 同步分支，执行不带 `--execute` 的 `r60_pilot5_v2_replay_execute.py` 离线预检，取得 `PILOT5_V2_REPLAY_PREFLIGHT_PASS__NO_REQUEST`。没有此回执不得调用模型。Owner明确批准后方可用双参数定向执行最多3槽位；严禁改v1、重复成功侧、自动扩批、训练/GPU或写DB。输出每阶段SAFE及不可变v2回执状态，继续独立裁决#2/#3/#4/#5、编制v1+v2只读crosswalk并用合成测试+CI验证。与其他Agent分支隔离修改、更新手册及Issue #26。不要回显任何私有正文/认证信息。所有训练准入保持0，历史System/R50/world/Owner独立性证据继续HOLD。

## 9. Owner Mac 预检已完成后的只读配对（2026-11-13 增量）

Owner 回传的 SAFE 如上，预检门禁已过。正式补审仅在 Owner 单独批准且两参数显式提供时执行既有冻结执行器，绝不重新调用7份有效 Reviewer，也不重新生成计划。

只读 crosswalk 现可在 Mac 上直接执行（不需要 API Key / 外发许可）：

```bash
"$PY" experiments/r58_quality/r60_pilot5_v2_crosswalk.py \\
  --quality-dir "$BASE/r60-quality-first-1000" \\
  --output-dir "$BASE/r60-pilot5-v2-replay"
```

首次运行应为 `PILOT5_V2_CROSSWALK_PARTIAL__QUALITY_HOLD`，`v1_cases=5`、`v1_valid_reviews=7`、`planned_slots=3`、`v2_recorded=0`、`unresolved_slots=3`。所有3份补审回执落盘并通过身份与Schema验证后，状态转为 `PILOT5_V2_CROSSWALK_INTEGRITY_PASS__QUALITY_HOLD`；其中失败回执仍然作为未解决槽位，不能重试覆盖或将格式成功视为文学质量 PASS。独立语义裁决与25条扩批决策仍HOLD。
