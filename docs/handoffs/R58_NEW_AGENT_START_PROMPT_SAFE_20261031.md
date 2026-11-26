# 新 Agent 启动指令 — StoryForge R58（直接复制下方正文）

> 本文为交接后的行动指令，并非任何私有数据、付费任务或训练操作的授权。日期 2026-10-31。

```text
你接手 StoryForge R58：GitHub sunxu/storyforge，分支 r58/roleplay-sft-skill-v01，Draft PR #7。

首先通过已连接的 GitHub 只读核查 PR 最新 HEAD、Draft/未合并状态，并完整阅读：
1. docs/handoffs/R58_NEW_AGENT_HANDOFF_SAFE_20261031.md
2. docs/handoffs/R58_NEW_AGENT_STATE_SAFE_20261031.json
3. docs/evidence/R58_OWNER_V02_80_PASS_RUFF_ZERO_POSTFIX_SAFE_20261031.json
4. docs/evidence/R58_G1_G2_SKILL_V02_READINESS_MATRIX_SAFE_20261031.json
5. docs/evidence/R58_G1_G2_EVIDENCE_RECOVERY_STOP_RULES_SAFE_20261031.md
6. docs/evidence/R58_G2_PINNED_REQUEST_ID_PERSISTENCE_SOURCE_AUDIT_SAFE_20261031.json
7. docs/evidence/R58_G2_DEPLOYMENT_SHA_SOURCE_PROVENANCE_SAFE_20261031.json

交接时已知：Owner Mac 80/80 单元测试 PASS、Ruff 0 错误；测试基准是修复 UP017/RUF007 后的 v0.2；不要再用旧文档的 47/61 测试数字作当前状态。此为代码验证，不代表真实训练输入或历史请求证据 PASS。

硬门禁：G1=HOLD，G2=HOLD，G3=NOT_STARTED，Train/Validation/Teacher 准入 0/0/0，expansion_allowed=false。Round1 固定 5 世界、上限 20 回复，已排除 1 个历史 SFT UUID 重叠世界，剩余 4 HOLD；不重新挑选候选。历史 Source pin RolePlay e9fe29c42434caeb0bac5acc91845ab4741ecb2b 不等于真实部署证明。

优先处理真实证据而非继续堆合成测试：
G1：确认已有的 CANCELED GPU Job 是否能找到与其直接绑定的原始 Trainer optimizer/global_step、checkpoint 和 Train/Val 输入 SHA256；已有 PRIVATE metadata 自洽但既不能证明更新发生也不能证明未发生。另补 R55/R56/R57、其他保护/保留世界的权威 UUID-only 来源索引。不要重新批量扫描历史日志，也不要因 CPU/CANCELED/ERROR 排除训练曝光。
G2：寻找已有的历史成功部署及回滚回执，证明三条冻结目标请求的 target-time 全量 Git SHA 与实际服务端；再寻找 target Assistant 物理消息↔API request_id 的直接因果证据，最后才审查当时真实 Provider dispatch 字节/参数。日志层 9/9 request_id join 不是 target join，软时间线 2/4/2 不能用来猜测；固定 RolePlay 源码的已审 Assistant 写入路径没有发现显式 request_id 持久化。DEPLOYED_SHA 会覆盖，workflow_run_id=manual-local-build 为字面量，旧 staging 有清理策略。没有现存部署回执时，不造数据、不必运行 g2_deployment_interval_audit.py。
阅读前述文档中的 SAFE 证据等级与停止规则。发现新的已授权原始来源才进行限定字段、只读验证；若无新增可信证据，明确报告 BLOCKER/HOLD，停止该支线。

禁止：改 main、合并/关闭 PR #7、触碰冻结 Skill v0.1、读取或上传 R50 密封题目/答案/故事原文/私有 UUID、上传 PRIVATE JSON、删除/覆盖旧私有回执、主动 SSH 生产 VPS、读取敏感日志/Job 命令/环境变量、启动任何付费 HF CPU/GPU、新训练、新推理、新数据冻结、模型晋升、扩大样本。所有敏感访问必须先取得 Owner 对具体范围的明确授权。SAFE 输出只含非识别性聚合/布尔/状态。

不要创建 docs/evidence/R58_ROUND1_PILOT_COMPLETION_SAFE.json，除非真实首轮双 Reviewer + Owner 审核已独立完成；其顶层状态 R58_ROUND1_PILOT_REVIEW_COMPLETE 才可能触发已有的每日只读扩样审批提醒，提醒本身并不授权扩样。

若需写 GitHub，只在当前 Draft 分支写可公开 SAFE 的代码、测试或证据文档，使用当前 HEAD 并回读核对；本地用户未提交更改不得覆盖。先向 Owner 给出简短状态及基于可信材料的一项实质下一步，避免反复让 Owner 重跑已通过的 80 项测试。
```

## 新会话第一轮推荐输出

新 Agent 应给出：（1）刚核到的 PR HEAD/Draft；（2）G1/G2 未清关理由；（3）能立即开展的一项**可核实的新证据路径**；（4）需要 Owner 明确授权的任何敏感读取范围。不能在没有一手证据的情况下宣布训练准入 PASS。

若连接器访问失败，应明确指出，改为使用已提供 SAFE 文档核对；**不要为省事索取或粘贴 PRIVATE 文件**。
