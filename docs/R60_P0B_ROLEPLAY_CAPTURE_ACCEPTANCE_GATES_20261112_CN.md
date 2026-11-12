# StoryForge R60 — P0B RolePlay真实生成留证联验前置核验与独立审批包

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
