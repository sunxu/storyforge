# R60 Base First-Train A/B：Mac私有证据定向裁决交接（2026-11-15）

## 当前已验证边界

Owner SAFE：`BASE_FIRST_TRAIN_AB_SCOPE_PRECHECK__NO_WRITES`与`BASE_FIRST_TRAIN_AB_SCOPE_BOUND__BOTH_HOLD`，文件已新建2份，DB/GPU/HF/model calls 0，Train 0。冻结336条中82条位于8组跨旧Train/Val相同world JSON（38 Story ID），另254条只是不在这些精确重复组里。两边Reviewer来源绑定通过，但独立Provider执行证据仍未通过。Codex 8组world语义盲审为7个`GENERIC_TEMPLATE`、1个`INSUFFICIENT_EVIDENCE`，全部隔离HOLD。合成System实际HF CPU3 Collator/R18 Mask通过，但不等于真实样本已准入。

**此刻不再新增批量来源扫描/模型重新评审/世界JSON提取。目标是Mac Agent读这两份既有私有结果和来源证据，给出最小证据裁决及可选首训集规模。**

## 两个源文件及保护规则

本地私有根：`~/.local/share/storyforge/r60/private`

- `r60-base-first-train-ab-scope-20261115/R60_BASE_FIRST_TRAIN_A_KNOWN_WORLD_RISK_PRIVATE.json`
- `r60-base-first-train-ab-scope-20261115/R60_BASE_FIRST_TRAIN_B_REVIEWER_EVIDENCE_PRIVATE.json`
- `r60-base336-world-cross-review-20261115/R60_BASE336_WORLD_CROSS_SPLIT_REVIEW_PRIVATE.json`
- `r60-base336-world-cross-review-20261115/R60_BASE336_EIGHT_WORLD_SOURCE_EVIDENCE_PRIVATE.json`
- `r60-base336-world-cross-review-20261115/R60_BASE336_WORLD_GROUP_DECISIONS_CODEX_PRIVATE.json`（如文件确实存在；需要单独验证合同、SHA和权限）

均只读、校验0600及SHA/对应roster绑定，禁止打印Story ID、正文、引文、账号凭证、URL secrets。不能确认具体原文时HOLD，不能凭上轮汇总数字伪造每组判决。

## A线：一轮定向判决，而非又一次八组提取

1. 从Codex**实际私有判决文件**确定唯一`INSUFFICIENT_EVIDENCE`的具体组ordinal，并重新校验8条判决与roster ordinal一致、世界原文引文准确。只读读取该组关联成员及其已有世界证据；如角色/Opening事实确实是最后缺口，**仅提取该组最少需要的匹配成员/版本**。禁止重启已HOLD的全量8组Card/Opening脚本。
2. 对其余7组，只在Codex报告明确提出独有角色、人物身份、剧情时间线或世界事实疑点时追加同等定向证据。通用world JSON同值不能自动合并Story为共享组件，但也不能仅凭Generic结论宣布真实情节隔离通过。
3. 对未命中8组的254条，优先只读检查**已有**R50及其他密封测试保护集、重复故事别名证据及历史冻结世界已知关系。未知保护范围的项只保持HOLD，不用未见内容推断`no overlap`。
4. 输出新版仅本地私有`R60_BASE_FIRST_TRAIN_A_DECISION_PRIVATE.json`（create-only、0600）：逐Story/案例绑定`confirmed_overlap / known8_exact_only / unknown_alias / exclusion_evidence`，将**证实边**建立图的连通组件；没有证实的边不能擅自合并，存在未决边者不可正式放行。只公开SAFE：检查案例数、风险隔离数、来源认证的候选上限与实际A门禁PASS数、完整R50/其他保护集状态、组件交叉数。
5. 若缺少R50完整保护清单或特定别名风险证据，一次性列出需要哪些文件/版本，不通过泛化搜索重新扫描1000条。不能把254当正式Train或将原276/60旧划分作为最终结果。

## B线：执行独立性证据强度分级

已核实代码：`r60_real_quality_batch.case_receipt`为同一Case依次对side A/B分别调用`r60_real_ai_dual_review.model_request`；`prompt_for_case`输入仅3条历史与target，不包含其他Reviewer评分；`model_request`每次新建请求/HTTP opener并禁重定向；V2/V3按`side`选择独立model/endpoint，保存来源SHA。**这是代码路径证明，不是不可抵赖的远端实际执行证明。**

1. 对336条每侧用现有crosswalk的`source=V1/V2/V3`和`source_receipt_sha256`映射到原始收据（全部现有，只读，不重新请求）。核对回执具体Provider配置、调用侧身份、同一Case是否依赖另一侧评分或回复；不得仅依据`method=ISOLATED_STATELESS_MODEL_REQUEST`或`owner_attested_independent_ai`推出PASS。
2. 证据分三级：`L1_SOURCE_RECEIPT_ONLY`（回执/配置，来源可信但执行独立未证实）；`L2_CODE_PATH_ISOLATED`（实际代码路径与请求模板可证，仍不代表远端实际调用）；`L3_EXTERNAL_EXECUTION_CONFIRMED`（来源绑定的时间、请求ID/Provider响应或等价可信执行记录，分别覆盖A/B且无串评）。把每条候选**两侧证据等级**分别记录，绝不捏造L3。
3. 能通过冻结协议的样本才可记Reviewer准入PASS；若没有Provider原始调用日志/已签的远端执行证明，统一`PROVIDER_EXECUTION_PROOF_HOLD`，但说明缺口在何处。核实Provider原始身份、模型ID、请求内容隔离与响应归属；不要要求重新对336×2调用模型。
4. 输出新版Mac私有`R60_BASE_FIRST_TRAIN_B_DECISION_PRIVATE.json`（create-only、0600），逐案例列双侧`source`、证据等级、缺失项和最终HOLD/PASS；对外仅SAFE汇总及缺证据分类，不输出模型秘密、原文及账户细节。

## 执行与验收要求

- 建议Mac Codex分别使用独立工作树完成A和B，不修改已冻结来源、Codex独立原始判决或训练数据；**本轮先使用已有文件作人工/模型语义审阅，不开发新批量泛化数据提取框架。**
- 原文必须本地处理。若Agent执行方式可能把私有小说/Review原文发往外部服务，先说明数据边界并取得Owner允许；不暗中上传。
- 输出最终两个SAFE JSON，分别报告A确证可隔离案例数、风险与未决故事数、B双侧L1/L2/L3覆盖数和候选PASS数；不能得到的数字保持unknown/HOLD，不能硬填。
- 即使A、B达PASS，也不可直接训练：还需最终真实样本SFT来源/版本构造、CPU Collator复验、明确GPU授权。始终`train_admitted=0`、`gpu_started=false`、`hf_jobs_submitted=0`。

## 面向Mac Agent可直接执行的任务要求

以本文件为权威任务书。先读取上述Mac私有证据、校验来源和权限；A/B分开审计、分别完成独立裁决私有文件与SAFE回执；对已知没有足够证据的项按HOLD处理。**不得只复制这份计划生成空模板，也不得只再次输出82/254范围统计。** 将实际能证明的证据强度和阻断原因提交SAFE，所有具体原文和Story ID仅保存在本地。
