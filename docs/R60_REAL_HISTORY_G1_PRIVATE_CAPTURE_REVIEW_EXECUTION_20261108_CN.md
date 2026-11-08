# R60-REAL-02/03：真实历史私有采集与独立质量审核执行说明（2026-11-08）

## 本轮状态与目的

**执行产物已提交且在本地合成数据测试通过；Owner Mac 的真实私有采集尚未执行。** 用户已明确授权以其拥有的真实历史数据推进 SFT，不再重复展开权益/协议讨论。仍需严格保障真实 User/Assistant 私密原文、私有 locator、R50 保护集与 Gold192 的隔离。

首批已用 ChatGPT 只读 Supabase 在生产库实际核对：**6 条连续四消息链**（User→Assistant→User→Assistant Target），覆盖 6 Story / 6 Session；Assistant 长度最短 301、最长 1,115 字；只返回聚合数字。上轮单 AI 实际初审 6 条建议 2 个玩家自主权严重排除、1 个安全严重排除、另外 3 个进一步审查；这些意见没有个案级私有证据锚定，**不得自动导入或冒充独立审阅结果**。本轮 SQL 也可能随生产数据库变化，不能凭临时编号确认与上轮六条完全相同。

代码：
- \`experiments/r58_quality/r60_real_private_batch.py\`：\`capture\` / \`template\` / \`review\`
- \`experiments/r58_quality/test_r60_real_private_batch.py\`：15 个无生产数据的合成测试
- 旧 Gold195/R58 \`quality_v1.py\` **未修改**，新实验线使用独立 Schema

## Owner Mac：可直接执行的最小命令

要求：本地已提供受控环境变量 \`STORYFORGE_SUPABASE_DSN\`，该 DSN 对应 **\`r58_export_reader\`**，只读、无 BYPASSRLS。**不要将 DSN 发到聊天或写入 GitHub。** 当前 ChatGPT 连接器的 \`supabase_read_only_user\` 因 \`BYPASSRLS=true\`，不能代替下列生产私有采集流程的身份门槛。

在 Owner Mac 的 StoryForge 仓库中运行（命令不会自动修改数据库或部署）：

\`\`\`bash
set -euo pipefail
umask 077
git fetch origin r60/gold192-history-v3-adapter
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter

python3 -m pip install 'psycopg[binary]>=3,<4'
install -d -m 700 "$HOME/.local/share/storyforge/r60/private"

BASE="$HOME/.local/share/storyforge/r60/private"
RUN="$BASE/g1-pilot01"
test ! -e "$RUN"
test -n "\${STORYFORGE_SUPABASE_DSN:-}"

python3 experiments/r58_quality/r60_real_private_batch.py \
  capture --output-dir "$RUN"
python3 experiments/r58_quality/r60_real_private_batch.py \
  template --capture-dir "$RUN"
\`\`\`

\`capture\` 在 \`REPEATABLE READ READ ONLY\` 事务中验证 \`current_user=r58_export_reader\`、\`row_security=on\`、\`rolbypassrls=false\` 和 \`rolsuper=false\`；仅对 16 个稳定抽样 Story 的每个最近 20 条 completed Assistant 筛选，**最多保留 6 个不同 Story 各 1 个目标**，要求上下相邻四条消息角色/状态精确一致，候选长度和技术元数据严格受限。它不会读取当前故事 Draft、不会获取 R50 正文、不会启动 GPU。

该次执行在 Owner 私有路径产生，均为新建不覆盖：
- \`R60_REAL_G1_CAPTURE_PRIVATE.jsonl\`：真实 ID、精确 turn、前序三条消息、目标正文、逐条 SHA256、目标语义；**0600**。
- \`R60_REAL_G1_CAPTURE_SAFE.json\`：仅计数/状态，不含 ID、正文、案例哈希。
- \`R60_REAL_G1_REVIEWS_PRIVATE.jsonl\`：\`template\` 生成的**未填写**独立 Reviewer 表单；不包含正文，但有私有 case key/哈希，仅留 Mac。

目录必须 **0700**、私有文件 **0600**，脚本拒绝输出目录已存在、路径不符、符号链接和未经许可 DB 身份。stdout 仅打印不含私有标识的 SAFE。

## Reviewer A/B 的私有审核约束

两个实际独立的审核者，各自读取同一 \`R60_REAL_G1_CAPTURE_PRIVATE.jsonl\` 的前序真实历史片段与目标文本，**不能直接复制上一轮未锚定的 6 条初筛意见**。逐条填写私有表单里的 \`reviews\`（两个不同 \`reviewer_key\`）、\`private_evidence_ref\`、1–5 分六维评分及三项严重旗标，必要时直接 \`REJECT\`。六维最低分：文学 4、人物一致 4、NPC 主动 3、玩家自主权 4、规则 4、叙事连续 4。

表单示意（字段为**虚构结构示意**，不代表已完成审核）：

\`\`\`json
{
  "schema": "storyforge_r60_real_independent_review_v1",
  "case_key": "<私有模板现有值>",
  "assistant_target_sha256": "<私有模板现有值>",
  "history_messages_sha256": "<私有模板现有值>",
  "reviewers_independent_owner_attested": false,
  "reviews": [
    {
      "reviewer_key": "reviewer-a",
      "decision": "HOLD",
      "private_evidence_ref": "private-evidence-a",
      "scores": {
        "chinese_prose": 4,
        "character_consistency": 4,
        "npc_initiative": 3,
        "player_agency": 4,
        "rule_fidelity": 4,
        "narrative_continuity": 4
      },
      "severe_flags": {
        "serious_player_agency": false,
        "hard_fact_or_ban": false,
        "safety_exclusion": false
      }
    }
  ]
}
\`\`\`

上例含不完整的审核员数量、\`HOLD\` 与 \`reviewers_independent_owner_attested=false\`，必定 HOLD。**绝不可直接把示例改成 PASS 或将一个 Agent 的两次同源判断谎称为独立 Reviewer。**

真实双审完毕后（需要补齐第二人并经 Owner 核验独立性），执行：

\`\`\`bash
python3 experiments/r58_quality/r60_real_private_batch.py \
  review --capture-dir "$RUN" \
  --reviews "$RUN/R60_REAL_G1_REVIEWS_PRIVATE.jsonl"
\`\`\`

输出 \`R60_REAL_G1_REVIEW_SAFE.json\`，只聚合 PASS/HOLD/REJECT 和固定原因码，仍 **train_admitted=0**。即使双审质量 PASS，必须单独验证完整的世界组件、目标前历史上下文、独立/完整的 R50 保护元数据以及 CPU Tokenizer/Collator，才能申请 GPU 批次授权；脚本不会自动把「质量 PASS」升级为「可训练」状态。

## R50 与 CPU 的当前硬门槛

- R50 **正文绝对不读取**。本轮仅检索过可见的 GitHub 代码检索入口，未找到能独立证明完整范围、版本和世界连接关系的 R50 保护全集元数据。不能由此推断它不存在；当前 \`R50_COMPLETE_EXCLUSION_UNKNOWN_HOLD\`。
- Story ID 不足以等价代表独立世界；跨作品别名/角色/共享资产等完整关系未知，世界连通组件与 Split **HOLD**。
- 实际生产提取 0（Owner Mac 尚未执行）→ 未形成冻结的私有真实训练集。本轮本地 Python CPU **15 项纯合成单元测试通过**；这**不是**真实候选的 Qwen Tokenizer、ms-swift Collator 或 HF CPU Job PASS，均保持待执行。
- 新实验线使用 \`DB_FINAL_PERSISTED_ASSISTANT\` 目标，只代表数据库最终持久化 completed 文本；历史 System 缺失不得用当前 Story Draft 回填，只可经过额外审阅的 \`RECONSTRUCTED_NOT_ACTUAL_SENT\` 规范化输入。

## 与 GitHub 受控协作库交换

\`sunxu/storyforge\` 当前 API 为 **Public**，只能提交代码、合成测试、脱敏统计。Owner \`sunxu/storyforge-owner-evidence\` 虽为 Private，当前 SAFE Schema 原为旧单对 40 pair 合同，**不得为了容纳新跨 Story 批次擅改 authorized_pairs=1 或直接上传私有 JSONL**。如需交换新六案例 SAFE，先为此独立批次设计并核验只含计数/原因码的版本化投影；不要传递私有 case_key、ID、哈希或正文。

**状态结论：\`G1_CAPTURE_PIPELINE_CODE_TESTED__OWNER_PRIVATE_CAPTURE_NOT_EXECUTED\`。两轨 train_admitted=0 / 0、生产 DB 未修改、RolePlay 未修改、R50 正文未读、GPU/HF Job 未运行。**


## 本轮 G0 分支谱系实际检查补充

生产列目录实际发现 \`story_v2_sessions.parent_session_id\` 和 \`forked_from_turn\`。按六案例同口径候选的**只读聚合**复核：6/6 对这两个字段均为空，计数 6 个 \`root_like\`。因此首批私有采集 SQL 已增加 \`parent_session_id IS NULL AND forked_from_turn IS NULL\` 约束，并新增测试；避免从明显的 forked Session 直接取局部历史就宣称已经重建完整目标前上下文。根会话标志不等于跨 Story 世界连通组件已经完整隔离。
