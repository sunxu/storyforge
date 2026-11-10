# StoryForge R60 — 新 Agent 主线交接总览（2026-11-08）

**交接状态：`G0_GLOBAL_REAL_DATA_DISCOVERED__P0_RIGHTS_AND_QUALITY_PENDING`。**  
**任务**：在不修改 RolePlay、无需重复 GPU 技术验证的条件下，从 Supabase 真实历史 User–Assistant 数据中筛出**合法使用、质量高、上下文可训练、世界隔离明确**的中文互动小说 SFT 数据，尽快推动正式 CPU→GPU 准入。Gold192/R50 与新实验线严格隔离。

## 新 Agent 一分钟接手

| 内容 | 实况 |
|---|---|
| 代码仓库 | `sunxu/storyforge` (Private) |
| 当前工作分支 | `r60/gold192-history-v3-adapter`；对应 PR [#25](https://github.com/sunxu/storyforge/pull/25)；未指示合并 |
| 主线跟踪 | Issue [#26](https://github.com/sunxu/storyforge/issues/26) |
| 受控协作仓库 | `sunxu/storyforge-owner-evidence` (Private), `main`；ChatGPT 已验证具有读写权限 |
| ChatGPT 连接器 | `StoryForge_Supabase_Read_Only` 的 `execute_sql` 可执行有界 SQL；实际身份 `supabase_read_only_user`, read_only=on、row_security=on、**BYPASSRLS=true**；无法切换为 `r58_export_reader` |
| Owner Mac Reader | `r58_export_reader`（read-only、RLS 不旁路）；本聊天不能直接访问本机文件或 DSN |
| 当前授权 G0 | 用户明确授权**所有 Story ID/Session ID**的聚合/只读元数据调查（已执行）。不是全站原文审核/训练同意 |
| 当前 G1 | 用户此前批准了**唯一 Story/Session**的有限私有 G1 审核（原 3 案已由 Owner Mac Agent 完成）；新其他故事 G1 暂无独立合法范围证明 |
| GPU 授权 | **无新的 GPU 训练授权；禁止自动提交** |
| 数据准入 | 严格 Gold192 **0**；真实最终回复实验线 **0** |
| 禁止 | 修改 RolePlay、数据库写操作/权限/RLS、读取 R50 正文、上传未经授权的真实对话、重复 GPU Smoke |

## 已执行、可审计的生产发现（不要重跑历史流水线）

### A. 跨作品有界 G0 Pilot

`docs/R60_GLOBAL_SUPABASE_METADATA_DISCOVERY_20261108_CN.md`、`experiments/r58_quality/sql/r60_global_real_history_aggregate_READ_ONLY.sql`：四类来源/可见性，每类 16 不同 Story、1 长 Session、20 completed Assistant 上限。64 Story、64 Session、1,280 completed、1,278 精确相邻 completed User、1,123 相邻且回复 >=300 字，523 达技术优先、涉及 55 个 Story ID（各类之和）；**不含内容/权限/世界审核**。此前独立 original/public 32 Story Pilot 640/365，也可能重叠，不能简单叠加。

### B. 作品作者等于会话参与者的新优先群

`docs/R60_REAL_HISTORY_RIGHTS_PROVENANCE_AUDIT_20261108_CN.md`、`experiments/r58_quality/sql/r60_author_player_original_private_aggregate_READ_ONLY.sql`：original/private/published/未删除的作品中，作者自己参与、30+ 轮的 Session 有 1,039 条（814 Story ID）。新独立有界 16 Story/16 Session Pilot 有 320 completed、320 adjacent、280 >=300 字、**77 技术优先**、10 Story ID。该分层用于优先查证许可，**不证明作者/玩家的训练同意**。与 A 可能重叠，不得汇总为净新增数。

### C. 权益来源目录审计

public schema 表/列名检查没看到可直接证明**所有文字对话都许可微调**的通用训练许可字段；`voice_consents` 与 `character_voices.consent_record_id` 是语音相关，不可套用于文字 SFT。不能据此宣称平台无合法授权；需继续调查版本化条款、历史授权、私有合同/证据。查询均不输出用户 ID、正文、DSN 或私有原件。

### D. 旧单对和原三案

Owner Mac G0 取得 40 Pair（80 消息元数据），原 3 案的目标 ID、目标 SHA、User–Assistant 相邻关系 PASS，447 个历史位置还可见；历史版本、System/Memory、Request/Attempt/单次 Provider 绑定 0/3；2 案 20–29ms created_at 逆序 UNKNOWN。三案暂停重复追溯，除非出现独立新证据。**没有可训练准入**。

### E. 既有模型试验和代码

R46 GPU LoRA SFT 7 步与 Adapter Reload PASS；R47 盲测完整性已做，但模型未正式晋升。**这不是 R60 新 GPU 授权**。GitHub 现有 `quality_v1.py` 六维质量地板可复用评价原则，不能直接伪装新实验线为旧封闭 `corpus=gold195/r58_round1`。  
`experiments/r58_quality/r60_real_history_metadata_triage.py` 是**唯一 Owner 单对 Scope 的 40 Pair 本机脚本**，要求 `r58_export_reader`；不能拿 G0 全域授权去给它填假 `r50_protected_scope_excluded=true`。  
本地 Owner Mac 独立分支 `r60/new-generation-evidence-pilot` `ca5ad67` 仅离线合成验证、未推送或部署；RolePlay 生产真实生成证据仍 HOLD，不是本轮阻断主线必做项。

## 权限矩阵（务必执行）

| 数据处理 | 可执行条件 | 当前 |
|---|---|---|
| G0：所有 Story/Session 元数据与聚合技术筛选 | 本次用户明确许可；read-only、bounded、不返回私人正文/身份 | **已执行** |
| G1：原授权单对有限私有内容审查 | 不扩用户/故事/用途，遵守原范围 | 原 3 案已完成；其余需核实限额 |
| G1：跨全库的真实内容质量审核 | 各来源/参与者/用途的独立可证权限，最小量读取 | **未获全库授权** |
| G2：正式训练使用与发布 | 作品与会话权益/隐私、历史版本/上下文、Quality-v1、世界/R50 完整隔离、冻结/CPU/Owner GPU 审批 | **0** |

连接器 `BYPASSRLS=true` 时，`row_security=on` 不提供有效的逐用户访问限制；必须在执行 SQL 的应用逻辑与源授权上双重约束。任何 SELECT 权限都不能自动等于训练合法。

## 两条独立训练路线

- `STRICT_GOLD_QUALITY_V1`：Gold192 冻结来源、旧 A/B 输入与监督目标链要求不变，独立 Train/Validation/保护世界证据。
- `REAL_HISTORY_FINAL_RESPONSE_SFT_EXPERIMENTAL`：可审核真实历史最终持久化 Assistant 作为监督目标（建议精确语义名 `DB_FINAL_PERSISTED_ASSISTANT`；**completed 并不证明已成功交付 UI 或是单次 Provider 原文**），真实历史 User/Assistant 上下文与显式 `RECONSTRUCTED_NOT_ACTUAL_SENT` 的规范化 System。该线**不是合成数据主线**，但也不能假称重建了历史实际 Prompt。权益、隐私、Quality、World/R50、CPU/Owner 批准照常逐项通过。

Gold192、原 R50 Held-out、本地三案、真实最终回复实验线不得混库、混 ID、混 Split、混来源语义；如世界联通跨来源，全部同 Split 或排除。

## 已提交的文件与完整阅读顺序

1. **`docs/R60_REAL_HISTORY_SFT_MAINLINE_CN.md`**：战略/优先级/实验线目标语义；
2. **`docs/R60_GLOBAL_SUPABASE_METADATA_DISCOVERY_20261108_CN.md`**：实测 64 Story / 523；
3. **`docs/R60_REAL_HISTORY_RIGHTS_PROVENANCE_AUDIT_20261108_CN.md`**：授权字段调查、作者参与群与 77；
4. **`docs/R60_REAL_HISTORY_NEXT_AGENT_P0_TASKBOOK_CN.md`**：立即执行的分步任务、证据格式和停止条件；
5. `docs/R60_REAL_HISTORY_40PAIR_TRIAGE_EXECUTION_CN.md`：旧单对 Owner Mac 40 Pair Python 路线，未宣称已实际执行新的 REAL-01；
6. `experiments/r58_quality/sql/r60_global_real_history_aggregate_READ_ONLY.sql`；
7. `experiments/r58_quality/sql/r60_author_player_original_private_aggregate_READ_ONLY.sql`；
8. `experiments/r58_quality/r60_real_history_metadata_triage.py` 与对应 `test_...`；
9. `experiments/r58_quality/quality_v1.py`：六维审查、保留原封闭 Schema；
10. `sunxu/storyforge-owner-evidence/README.md` 与 `docs/SAFE_EXPORT_POLICY_CN.md`：只允许 SAFE 聚合，不允许未经授权的生产原文上传。

## 下一 Agent 的 24 小时工作安排（非后台调度承诺）

**P0-1：现有资料一次性核对**（PR #25/Issue #26/上述 10 项，当前分支与 CI，是否出现新 SAFE）；如 Owner evidence 新仓 `packets/safe/r60-real-01.json` 缺失，不捏造。

**P0-2：真实权益来源调查，停止条件明确**：在可访问的历史条款/授权审查材料里找到文字对话微调/内容审核许可的实际依据和版本生效时间；先关注作者参与 original/private 群，不以其身份相等跳过验证。如果没有来源，立即产出清晰 `RIGHTS_EVIDENCE_SOURCE_UNAVAILABLE` 和一次性补证要求，而不是循环查数据。

**P0-3：允许 G1 的小批真实文学审核**：仅在有可验证的内容审核许可后对同一世界来源至多 5–10 条定点取必要正文，按 Quality-v1 六维由独立 Reviewer 评分、记录严重问题，真实目标/历史输入语义准确。否则只推进纯代码/受控 metadata，绝不依赖全站 BYPASSRLS 导出原文。

**P0-4：并行 R50/世界元数据完整性**：只能用已授权且经独立证明完整的 R50 保护范围元数据，不读题目/正文。世界组件/跨 Story 依赖证明不足则 HOLD。

**P1：只有在 P0 实证充足后才构建新数据的私有训练清单、CPU Collator、显式 GPU 预算授权。**

## 非目标与交付

不得要求用户提供明文 DSN/密码、自动提升 RLS、修改 RolePlay、提交 HF GPU Job、把真实用户隐私放 GitHub、重新开发重复的模拟 SFT 或无意义扩样计数。GitHub 只能提交代码、文档、合成测试与严格脱敏 SAFE；Owner 本机私有原件仍留在 Mac。

每个工作阶段返回：本轮真实动作、聚合结果、阻断/不确定项、Git Commit/文件、下一步可执行事项；避免反复生成 HOLD 报告代替实际调查。**两轨训练准入均为 0，不允许自动晋升。**
