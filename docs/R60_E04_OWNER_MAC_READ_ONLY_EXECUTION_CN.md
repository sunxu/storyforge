# R60 E04 Owner Mac 只读核证执行令（已获用户授权）

> 授权范围：用户已明确授权本机 AI Agent **只读**核验 R60 E0–E3 证据与独立 Validation 候选，并声明 Gold192 由其拥有或已获授权用于模型微调。此声明是**来源权益审核线索/Owner 声明**，不是自动覆盖每条作品的使用权、第三方内容、个人隐私、来源版本和传播授权的可认证证明。
>
> 本文是交给运行在 Owner Mac 上的 Agent 的执行令；提交此文件本身**不代表已经访问私有目录或通过核证**。

## 执行目标（不再制造模板）

在已有三案语义 3/3 PASS、三案跨案例依赖为单连通组、0 个 Owner 证据签核的基础上，**逐案核证可取得的现有可信证据**，同时只从已有的**冻结候选库存和经批准的 Owner 本机元数据**中筛选可能独立的 Validation 世界；不得以“找到了文件”代替实证结论。

### 强制只读边界

- 所有源文件只读：`$HOME/.local/share/storyforge/r59/private` 下既有 P2/P3/E03/AI 审核/跨案例依赖记录、既有 Owner 证据及冻结清单，必要时只读 `r58/private` 既有证据。先检查 0600 权限、上游 SHA 和未被替换状态。
- **不访问生产 Supabase / 数据库，不主动查询连接器**：这次授权是对“本机既存证据”的只读核验；若必须触及远端库，先独立申请明确授权。
- **不写入或修改任何已有源文件**。允许只在新的本机私有输出目录（0700）中创建核证回执（0600，不覆盖），不向 GitHub 上传私有数据。
- 不触碰 R50 本文或题目；保护集只使用**已授权的完整元数据清单**及版本指纹，不能虚构完整性。
- 不启动 GPU、HF Job、外部模型推理或任何付费计算；不进行训练；不修改生产配置。禁止重新运行 P1–P6、历史大范围搜索及性能扫描。
- 不以“人工已授权微调”推出第三方作品、版权、隐私、许可条款全部已核证。只能记录 Owner 声明存在，具体案例证据不足仍为 HOLD。
- 所有故事正文、用户消息、案例 ID、世界 ID、原文引用、私有路径和案例级 SHA 均不可输出到 SAFE、终端公开日志或 GitHub。

## 核证工作流

### A. 锁定三案原件与已验证状态（无内容重审）

1. 只读取 **同一可信批次** 的 `R60_E03_SEMANTIC_REVIEW_PRIVATE.jsonl`、`R60_E03_REVIEW_LOCATORS_PRIVATE.jsonl`、`R60_E03_AI_SEMANTIC_RESULTS_PRIVATE.jsonl`、`R60_E03_AI_REVIEW_SAFE.json`、`R60_CROSS_CASE_DEPENDENCY_PRIVATE.json` 及其 SAFE。
2. 校验三案同一身份/目标 SHA、输入 SHA、SAFE 相符；AI 3 PASS、全部确定性验证、单个 3 节点依赖分组；每项不符合直接 HOLD，并报告**固定原因代码**，不暴露私有 ID。
3. 不重新调用 Reviewer、SFT Shape Packer、Packet 扫描或跨案例依赖器，除非出现可复核的原件完整性失败。

### B. E0 来源权益与隐私（Owner 声明已收到但不可自动 PASS）

每条核对：冻结版本原件；作者/权利归属或明确许可范围；使用权是否涵盖模型微调；是否有第三方素材及其许可；私人对话和可识别个人信息的隐私边界、脱敏/同意依据。将本次 Owner 使用权声明记录为 `OWNER_GENERAL_RIGHTS_ASSERTION_PRESENT`，而不是 `rights_attested=true` 的案例级结论。每个 PASS 必须有对应作品、来源指纹与可核证权限依据；缺则 HOLD。

### C. E1 重建透明度

逐案核对冻结 Stage、来源 Packet、System 版本、历史可见范围、明确截断前缀/清洗规则、记忆注入/世界卡时点的独立记录。重建输入必须保留 `RECONSTRUCTED_NOT_ACTUAL_SENT`；禁止标为实际 Provider Payload，禁止根据当前世界卡导出快照“回填历史”。只读材料无法证明的环节，列出未知假设，HOLD。

### D. E2 监督目标与处理链

只从已有 Owner 文档寻找能证明最终目标是否来自单次完整 Assistant completion 的可信记录；区分 UI 交付文本、过滤、重试、续写、拼接与单次 Completion。Packet 目标逐字一致不等于单次 Provider Completion。没有可靠证据就 HOLD；不要再重新搜索缺少 Request/Attempt 提示的旧 25 案材料或推断不存在的请求链。

### E. E3 世界/曝光/保护集与独立 Validation 发现

1. 本次三案字面依赖组**必须是同一 split**。不能假定它就是全部世界组件。
2. 使用现有 `quality_v1.py`、`r59_evidence_inventory.py`、`r59_owner_evidence_preflight.py` 的只读/纯函数能力核对世界组件、来源 pins、Train/Validation/Test 历史曝光和授权保护集**元数据**。空集、缺失或不完整清单不算 verified false。
3. 从**已有冻结的 28 条候选以及既有经批准的其他库存的元数据**中寻找不同世界，优先只读世界身份、来源 SHA、审核状态、曝光标记和证据引用；既有 25 条无请求线索，不能当成已证实训练/Validation 可用。不得读取 R50 资料来构建 Validation。
4. 若存在不同故事 ID，但世界组件未证明隔离，状态保持 `WORLD_ISOLATION_UNVERIFIED`；候选出现语义/字面依赖、历史污染或版权不明，必须排除或 HOLD。
5. 只在证据同时足够且与本组三案无交叉依赖/同世界时才报告 `VALIDATION_WORLD_VERIFIED`；否则 `INSUFFICIENT_INDEPENDENT_VALIDATION_WORLD`。

## 输出规范（Owner 本机新目录，只写报告，不改原件）

新建 `$HOME/.local/share/storyforge/r59/private/r60-e04-owner-evidence-<UTC_TIMESTAMP>-<PID>/`（0700，输出 0600，不覆盖），文件：

- `R60_E04_OWNER_EVIDENCE_DECISIONS_PRIVATE.jsonl`：3 条逐案 E0–E3 决策及原件 SHA、可复核引用/不确定项；记录总授权声明，区分案例级权限证据；不能凭空 Owner 签核。
- `R60_E04_VALIDATION_WORLD_CANDIDATES_PRIVATE.jsonl`：已检查候选的世界归属、依赖组、历史曝光、保护集元数据证明和是否可用；未知值保持 unknown。
- `R60_E04_OWNER_READ_ONLY_SAFE.json`：仅 SAFE 聚合计数、是否存在可验证独立 Validation 世界、主要 HOLD reason_code，以及 `database_modified=false`、`gpu_started=false`、`r50_accessed=false`、`quality_v1_admitted=0`、`training_authorized=false`。
- `R60_E04_OWNER_REVIEW_REPORT_PRIVATE.md`：详细中文核证报告与**具体尚缺的证据种类**，但不得在公开对话直接贴内容。

## 验收/停止条件

1. 只读核证三案的 E0–E3：每案可证即证，不能证就 HOLD 并给出固定缺口原因；不得为了凑训练样本自动标记 PASS。
2. 证明本三案同一 split 限制被保持，未用故事 ID 代替世界隔离。
3. 证据充足时才报告独立 Validation 世界；否则输出 `INSUFFICIENT_INDEPENDENT_VALIDATION_WORLD`。
4. 不访问远端库、不访问 R50、不创建 GPU Job、不调用外部付费模型、不写入或修改既有源文件。
5. SAFE 如实记录：总声明已收到，但 **`e0_e3_owner_verified` 仅由真实可审计的证据及签核决定，不能根据用户消息自动变为 3**。
6. 当前 E4/E5/E6 都仍是 HOLD/未授权；只在 E0–E3 可信证据完备后提交单独决策，不得自动进入训练。

**直接执行核证。不要再次仅提交一份审核任务书，也不要为了“继续推进”新增重复扫描器；如源文件不在本机执行环境，明确报告环境无法访问，不能假装已经读取。**
