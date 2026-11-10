# R60 REAL-02：真实历史六案例首轮内容筛查 SAFE（2026-11-08）

**状态：`REAL_HISTORY_G1_SIX_STORIES_AI_SCREENED__INDEPENDENT_QUALITY_REVIEW_PENDING`。**

## 实际执行

- Owner 已明确决定本项目可使用其真实历史数据用于训练；该决策下不再做协议来源调查。后续只追踪技术质量与模型输入验收。
- 使用现有只读 `StoryForge_Supabase_Read_Only.execute_sql` 实际读取 6 个不同 Story 的 6 条真实 `completed` Assistant 回复、精确相邻 `completed` User 和可用的前一轮 User/Assistant 片段。选自 `original/private/author==session_player` 的已发布、未删除长 Session；数据库读取有界，每 Story 1 个案例；筛选目标 300–1500 字，正常 finish，无显式编辑或解析警告。
- 仅在受控对话/工具会话内临时审查文字。**没有把实际消息、Story/Session/User ID、个案 SHA、私有原件或可逆标识提交到 GitHub。** 未生成可回放的 Owner 私有案例定位包；本次查询只输出无身份编号。
- 监督目标语义 `DB_FINAL_PERSISTED_ASSISTANT`；无历史 System/Memory 版本证明，不能声称 `ACTUAL_SENT`、Provider 原始单次输出或 UI 实际交付。上下文只覆盖紧邻局部片段，不能声称完整世界规则或历史上下文核证。
- 可复现的只读 **G1** 审核查询：`experiments/r58_quality/sql/r60_real_history_g1_six_case_private_review_READ_ONLY.sql`。SQL 含真实正文，**禁止在 CI、公有日志、GitHub 评论中运行/打印结果**；重跑时数据可能因生产变化改变，逐案例 Locator 只能留 Owner 本机私有空间。

## 单名 AI 首轮筛查结果（非两位独立 Reviewer）

| 指标 | 计数 |
|---|---:|
| 真实 Assistant 目标实际审阅 | **6** |
| 不同 Story | **6** |
| 精确相邻 User 与局部历史片段随同审阅 | **6** |
| 建议因严重玩家自主权问题排除 | **2** |
| 建议因严重内容安全问题排除 | **1** |
| 其余需更多质量/世界规则复核 | **3** |
| 完成两位独立 Reviewer 的六维质量 PASS | **0** |
| 完整历史世界约束已核实 | **0** |
| R50 全集保护元数据已核实 | **0** |
| 训练准入 | **0** |

这是一名 AI 对实际真实正文做的**初筛意见**，并非第二名独立审阅者，也没有 Owner 本机可重放的逐案审核记录。六维观察覆盖中文表达、角色表现、NPC 推进、玩家自主权和局部连贯性；**`rule_fidelity` 无历史世界版本无法完整判定**，不得假造分数或强行按原 Gold195 封闭 `quality_v1.py` Schema 声明 PASS。未审案例也不能被反推为安全或优质。存在明显严重问题的目标应从后续候选中优先剔除，完整结论须有 Owner 私有精确 Locator 与独立审核复验。

## 下一步纯技术动作

1. 在 Owner 私有 0700/0600 空间，以精确 ID+消息散列锁定本轮抽样或下一批 5–10 条，形成不可公开的 `R60_REAL_G1_CASE_LOCATORS_PRIVATE.jsonl`；先审核是否跨作品重复，不能只靠行号复现。
2. 第二名独立 Reviewer 对保留案例执行六维评分并验证严重问题；一票严重缺陷拒绝。将原案质量审核与新的实验轨 `REAL_HISTORY_FINAL_RESPONSE_SFT_EXPERIMENTAL` 分开，不修改 Gold192。
3. 按真实历史 User/Assistant 边界构建目标前输入；规范化 System 标记 `RECONSTRUCTED_NOT_ACTUAL_SENT`，禁止将当前 Story Draft 当历史组件。
4. 用**完整、独立证明的** R50 保护全集元数据（仅身份/世界关系、不读正文）与世界连通组件处理独立 Split。未知保持 `R50_EXCLUSION_UNKNOWN_HOLD` / `WORLD_COMPONENT_UNKNOWN_HOLD`。
5. 完成独立数据 Schema 后，在 CPU 上校验 tokenizer 与 collator；独立预算授权前**不运行 GPU**。

## 不变量

```json
{
  "schema": "storyforge_r60_real_g1_first_screen_safe_v1",
  "status": "G1_SIX_REAL_CASES_AI_SCREENED__NO_QUALITY_V1_ADMISSION",
  "real_targets_screened": 6,
  "distinct_stories_screened": 6,
  "single_ai_suggest_reject_agency": 2,
  "single_ai_suggest_reject_safety": 1,
  "single_ai_hold_for_further_review": 3,
  "independent_dual_review_complete": 0,
  "source_world_version_verified": 0,
  "r50_full_metadata_exclusion_verified": 0,
  "strict_gold_train_admitted": 0,
  "experimental_train_admitted": 0,
  "raw_text_or_real_ids_pushed_to_github": false,
  "production_database_modified": false,
  "roleplay_modified": false,
  "r50_body_accessed": false,
  "gpu_started": false
}
```

**注意**：上一轮 64 Story/523 和作者参与 16 Story/77 技术优先是另一时间的技术筛选结果，与此 6 条筛查可能重合；不可相加为独立样本量。
