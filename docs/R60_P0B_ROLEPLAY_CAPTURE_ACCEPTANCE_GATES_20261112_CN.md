# StoryForge R60 — P0B RolePlay真实生成留证联验前置核验与独立审批包

## 2026-11-12 P0B数据库结构现场只读验收：完成，运行态仍未验收

已从**可用的StoryForge Supabase只读连接器**（非Owner Mac本地日志推测）实际运行三组纯SELECT，且将复用SQL固化至`experiments/r58_quality/r60_p0b_roleplay_capture_readiness_readonly.sql`并原样再次执行通过。聚合SAFE schema `storyforge_r60_p0b_roleplay_capture_readiness_snapshot_v1`，当前返回`DB_STRUCTURE_ONLY__RUNTIME_AND_CAPTURE_AUTHORIZATION_HOLD`。**没有采集、创建grant、改SQL或导出原文**。

| 数据库门禁 | 当前真实只读证据 | 判定 |
|---|---|---|
| 基础留证表/访问表 | `v2_generation_evidence`、`exports`、`grants`、`request_links`、`access`、`grant_operations`六表实际存在 | DATABASE_STRUCTURE_PRESENT |
| 迁移登记 | `v2_generation_evidence_expand`、`export_access`、`grant_control`、`request_links`、`lifecycle`五份各登记一次 | MIGRATION_REGISTRY_PRESENT，不代替实际源码/函数指纹验真 |
| 表级访问 | 六表`relrowsecurity=true`，`anon`与`authenticated`没有表级SELECT | BASE_TABLE_READ_ACL_PASS_ONLY；**不证明其它可访问函数/视图/继承角色或实际Worker端凭据配置均安全** |
| 留证记录 | 六表记录数全0 | NO_CAPTURED_DB_RECORDS，不能建立P1真实留证池 |
| Worker/采集/导出/网关 | 本连接器不能观察PM2/systemd、worker process、开关、TLS与外连 | RUNTIME_UNVERIFIED |
| 真实请求/供应商与费用 | 未发真实Provider请求、无independent witness/体验/计费结果 | P0B_HOLD |

**本轮只读SQL复用方式**：在Owner已批准的只读Supabase查询环境中执行`experiments/r58_quality/r60_p0b_roleplay_capture_readiness_readonly.sql`，只返回JSON SAFE结构。该脚本输出六表聚合计数、RLS/表级读取权限、五份关键迁移登记，不含任何私人ID/正文/DSN、故事文本、权限token；其他环境的运行要用同样只读账户并核对数据库身份。不要拿本次聚合结果冒充真实Worker/TLS/Provider验收。

**下一优先动作（只读且不改变正常聊天）**：由RolePlay生产所有者在原有受控`ops/evidence/preproduction-checklist.md`和`ops/evidence/README.md`下核对实际应用部署SHA（不同于仓库HEAD）、独立Worker/systemd安装与启停、采集/导出/授权开关、加密私有对象存储与TLS网关配置是否满足要求，**仅返回SAFE存在性/版本/开启状态/缺项计数**；不要粘贴环境变量的值、密钥、IP或完整用户数据。拿到运行态只读证据之后才具备判断P0B真实合成联验需要何种独立操作审批的依据。**当前仍禁止真实Provider/生产采集、迁移、Grant和训练。**


日期：2026-11-12。**状态：DRAFT_ONLY_NOT_AUTHORIZED**。引用[新SFT优先级任务书](R60_SFT_NEW_EVIDENCE_FIRST_EXECUTION_20261112_CN.md)。

## P0A已完成到什么程度

Owner Mac的真实回执表明`v2-evidence-acceptance-preflight/1`在`mode=draft`校验成功，但`requestState=DRAFT_NOT_AUTHORIZED`、`preflightPassed=false`、`executionAuthorized=false`，不是可执行审批。69项预检反例+8项CLI、独立转发见证合成矩阵、消费者31项反例均PASS；真实Provider/真实chat体验/真实工单身份认证未执行。Owner本地备份见`RolePlay/.claude/temp/v2-provider-witness/1794447385440-29103/{result.json,temporary-files.json}`，不上传含原文的结果。

此前只读Supabase现场：`v2_generation_evidence`、`v2_generation_evidence_exports`、`v2_generation_evidence_grants`、`v2_generation_evidence_request_links`全部0行。此时**不能建立P1真实留证候选池**，也不得将日期在2026-11-10发布之后的普通消息误称为完整留证。

## P0B九个独立外部验证门禁

| Gate | 明确待交付物/验收 | 未满足时状态 |
|---|---|---|
| APPROVAL_AUTHENTICITY | 来源可信的单独批准记录、审阅人/执行人/撤回人与工单号，绑定申请原文SHA256及限定窗口 | HOLD |
| ENVIRONMENT_AND_ARTIFACT_IDENTITY | 目标VPS/DB及服务版本现况只读比对、git完整源码SHA、正式Worker制品manifest SHA、实际配置开关/有效用户 | HOLD |
| SQL_EXECUTION_AND_PROBES | 只读查实际SQL历史/对象/函数/RLS/ACL和延期候选；已执行17份不重复执行，额外迁移须逐份独立批准 | HOLD |
| RUNTIME_ACCESS_AND_RESOURCE_LIMITS | Worker用户/文件权限、CPU/内存/IO/队列/对象储存、加密和密钥轮换、保留期及撤回能力的现场证据 | HOLD |
| LIVE_BUDGET_ENFORCEMENT | 选定确切协议+型号及真实当前价格依据、物理调用总数/每次token/总费用硬限制、异常保守停发 | HOLD |
| GRANT_CONTROL_AND_TLS_GATEWAY | 最小授权范围的受控grant、权限撤回、TLS接入与私有出口；不得通过公网临时开放原文 | HOLD |
| INDEPENDENT_WITNESS | 同一次真实调用的独立出口接收者/独立转发见证，逐字节关联所有Provider attempt；未观察到relay最终出口保持对应HOLD | HOLD |
| CHAT_EXPERIENCE_AND_BILLING | 首字、流式间隔、取消/重试、P95、内存/IO、异常率和实际扣费，与无留证基线相比达预先批准阈值 | HOLD |
| STORYFORGE_SIGNOFF | Owner单独核验完整manifest/witness/target一致性、来源边界、匿名导出和后续数据许可/质量门禁，不以工具PASS代签 | HOLD |

**以上九项仍然都是外部未完成项；不要因为P0A合成PASS将其自动转绿。** 当前仅收集这些门禁的只读证据、职责、验收标准，不执行任何改变生产系统的动作。

## 重用RolePlay已实现操作入口，不造第二套Capture

- `sunxu/RolePlay/ops/evidence/preproduction-checklist.md` — 既有运行前清单。
- `ops/evidence/acceptance-request.example.json` — **默认全部false、不可直接授权的申请模板**。
- `ops/evidence/validate-acceptance-request.mjs` — 先`--mode draft`；只有全部独立审批及真实环境条件确认后，才考虑`--mode ready`，且ready也不自动执行。
- `ops/evidence/provider-witness.md` — 单个合成场景的有限费用独立见证；不能作为正常用户请求随意引入代理。
- `ops/evidence/verify-bundle.mjs` — 接收独立导出/witness/目标结果的独立校验；缺来源认证不得提升证据等级。
- `ops/evidence/README.md` — Worker与生产访问实际门禁。正常聊天采集/导出默认关闭。

Owner仅在**无生产凭据、无实际用户正文的RolePlay本机工作树**复核：

```bash
set -euo pipefail
cd "$HOME/workspace/RolePlay"
git rev-parse HEAD
git status --short
node ops/evidence/validate-acceptance-request.mjs \
  --request ops/evidence/acceptance-request.example.json \
  --mode draft
node scripts/check-v2-generation-evidence-preflight.mjs
node scripts/check-v2-generation-evidence-witness.mjs
node scripts/check-v2-generation-evidence-consumer.mjs
```

记录固定`git rev-parse HEAD`、合成result.json及temporary-files.json的SHA256、测试结果与代码变更说明；**不能从仅有复制的PASS文本推定这次运行的精确源码SHA或独立结果文件完整性**。Owner返回不含用户身份/原文/真实DSN的SAFE统计即可。随后对照现有RolePlay production release文档执行只读环境状态审计，并形成一份零写操作的差异清单。

## 本期执行许可界限

用户确认的是**SFT数据来源与优先级**、离线合成验证推进，不是允许安装Worker、修改生产DB、启用采集/导出、签发grant、真实付费外连、读取所有用户请求原文或训练GPU。任何工单若仍为空模板、审批不完整、未能核对实际型号/费用、未能独立见证或未验证性能与回滚，应当停在`P0B_AUTHORIZATION_AND_ENVIRONMENT_HOLD`。

**目标结果：`P0A_SYNTHETIC_TESTS_PASS__P0B_PREPARATION_ONLY__CAPTURE_NOT_ENABLED__TRAIN_0`。**
