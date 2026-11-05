# RolePlay → R58 只读库存基线

查询日期：2026-10-30；来自用户提供的 Supabase 只读连接。数据库模式 `transaction_read_only=on`。

| 项目 | 基线数值 | 证据属性 |
|---|---:|---|
| public 基础表 | 296 | 元数据查询 |
| user_stories | 5,005 | `COUNT(*)` 精确 |
| 未软删除故事 | 4,991 | `COUNT(*) FILTER` 精确 |
| V2 sandbox 故事 | 4,968 | `COUNT(*) FILTER` 精确 |
| moderation approved | 1,213 | 精确 |
| moderation override_approved | 318 | 精确 |
| 符合“未删+已批+original+完成≥50”的故事 | 1,108 | 精确计数；Assistant 数由物化汇总表给出 |
| V2 sessions | 196,149 | `COUNT(*)` 精确 |
| V2 sessions deleted_at IS NULL | 166,585 | 精确 |
| V2 sessions turns≥30 | 24,982 | 精确；含其它状态会话，不等于准入 |
| V2 messages | 约 630 万 | pg_stat 估算 |
| V2 messages storage | 约 29 GB | 包含表与索引 |
| analytics_story_lifetime completed assistant | 2,838,545 | 物化汇总累计值，不等于可训练样本数 |
| v2_data->world 结构 | 4,968 | JSON 类型/键元数据 |
| v2_data->character 结构 | 4,968 | JSON 类型/键元数据 |
| v2_data->director 结构 | 4,968 | JSON 类型/键元数据 |
| story_admin_versions | 0 | COUNT(*) 精确 |
| 无法联结到当前 user_stories 的 V2 session | 3,952 | 只读左连接精确计数 |

## 已确认事实与待核验
- `v2_chat_messages` 至少存在 `user/completed`、`assistant/completed`、`assistant/failed`，来自小比例块抽样，不能推断全量率。
- RolePlay 有大量可发现的故事与对话，**但还没有任何真实记录被本 Skill 正式准入**。
- 目标准备过程中必须另行拿到当时真实的 System、故事卡、角色规则、分支历史及相关状态；不能以现时 `v2_data` 代替。
- Owner 对角色、内容合法合规及训练使用权已作总体确认；这不是对运行时重放和 SFT 质量的替代。
- 项目 R50 不访问，历史 Gold195 已有回执要复用，不重复重审 PASS 部分。
