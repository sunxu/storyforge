# StoryForge Gold Quality Pipeline

## Purpose

One private append-only event Manifest for frozen source pins, legacy review evidence, historical exposure, incremental blind reviews, exclusions and adjudication. The CLI is an audit orchestrator, not a reviewer or training-admission shortcut.

Keep exact-target exposure, UUID exposure and semantic world-component isolation separate. Keep Gold87 selection evidence separate from its row metadata; keep Gold108 legacy five-dimension review separate from Quality-v1. Preserve Reviewer A/B disagreement as distinct events.

## Install and commands

```bash
python -m pip install -e .
storyforge-gold-quality inventory
storyforge-gold-quality verify-source --repo-root "$PWD"
```

Supported commands: `inventory`, `verify-source`, `import-history`, `import-exposure`, `append-review`, `append-exclusion`, `validate`, `report-safe`.

The private Manifest must live outside the Git checkout in a directory with mode 0700; the file is created with mode 0600. Writes are append-only and use no-follow file opening. Same-case target hash changes fail closed.

## Import contracts

- Gold87: one batch-level `LEGACY_SELECTION_EVIDENCE` event (87 cases, selection recorded, reviewer independence unproven) plus 87 row-level `SOURCE_METADATA` events (`independent_gold_review=NOT_RUN`, single Curator scores).
- Gold108: first run the existing `gold108_review_binding.py` and require its exact SAFE PASS status. Import 108 row-level `LEGACY_REVIEW` events and one batch-level binding receipt. Keep rubric `FIVE_DIMENSION_LEGACY`; `new_quality_v1=false`.
- Gold195 exposure: safe aggregate imports remain aggregate-only and set case-level exposure to `UNKNOWN_NOT_IMPORTED`. Row-level import requires the original R57 private ledger and the SAFE receipt from the same run proving source byte pins. No aggregate-to-row synthesis.
- Gold192: A/B/AI/adjudication events remain separate. The three unresolved-world exclusions are separate `EXCLUSION` events. Each review row carries six 1–5 scores and a reviewer role.

## Privacy and non-authorization

SAFE output contains counts only; never emit case IDs, story UUIDs, prose, alias maps or row-level target hashes. Quality-v1 admission remains zero; training, GPU and R50 access remain false. Tokenizer preflight continues to reuse only `src/storyforge_dataset/token_preflight.py`.

## 只读适配器：实际执行合同

统一入口现在提供 `run-check` 子命令，**只允许三个不需要私人文件路径参数的 SAFE 检查**：

| --check | 复用源码 | 只输出 |
| --- | --- | --- |
| `gold87-legacy-index` | `gold87_legacy_index_audit.py` | 已验证行数与身份数量 |
| `gold108-legacy-binding` | `gold108_review_binding.py` | 旧双审索引与证据绑定数量 |
| `gold195-target-source` | `gold195_target_source.py` | 目标结构验证数量 |

```bash
storyforge-gold-quality inventory
storyforge-gold-quality verify-source --repo-root "$PWD"
storyforge-gold-quality run-check --check gold108-legacy-binding --repo-root "$PWD"
storyforge-gold-quality run-check --check gold195-target-source --repo-root "$PWD"
```

执行器使用固定的源码相对路径和固定参数，校验脚本不为 symlink 且仍位于该 Git checkout，限定执行时间、CLI 返回状态、Schema、状态字符串和整数计数。任何失败均 HOLD；既有脚本的 stdout/stderr 原文**不会直接透传**到统一输出。

其余注册的 R57/R58 工具目前只是 *inventory 元数据*，不等于已接入可执行入口。涉及私人路径、逐案文本、审核写入、模型 Tokenizer 或冻结操作的工具，必须先定义显式输入与 SAFE 输出合同并单独增加回归测试；不能通过自由拼接任意命令运行。Tokenizer / Chat Template 预检只允许使用既有共享核心，并且真实模型特定工作只在 HF CPU 执行。

### SAFE 输出边界

- 已知批次仅输出 `gold87`、`gold108`、`gold192`、`gold195`；其他批次聚合为 `OTHER_PRIVATE_BATCHES`。
- 未知 decision / evidence_tier 标签聚合为 `OTHER`，不得把任意标签直接当作 JSON key 输出。
- SAFE 聚合不包含逐案 case_id、story UUID、target hash、原文、模型输出或自由文本。
- Gold87 Index `ACCEPT` 仍只是历史登记，不等于逐案独立审核；Gold108 五维双审与 Quality-v1 六维双审不得混为一谈。
- 目前没有任何私有数据导入，也没有使 Quality-v1 admission 非零。

### 测试与兼容

专用 `.github/workflows/gold-quality-pipeline.yml` 校验新代码 Ruff、冻结 Git Blob pin、统一 CLI 合成测试、SAFE 适配器合成测试与 R57 回归测试。全仓历史 Ruff 失败单独报告，不篡改不相关旧源码。

## Reviewer B 唯一有效版本（2026-11-02）

当前 Owner 指定的 Reviewer B 原始结果通过 SHA-256 固定为：

- 文件：`R58_GOLD192_REVIEWER_B_RESULTS_20261102(3).json`
- SHA-256：`bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8`
- Schema / 状态：`r58_gold192_reviewer_b_results_v1` / `REVIEW_COMPLETE`
- 192 条；PASS 178、HOLD 12、REJECT 2；192 个 blind ID、target SHA 均唯一。

只在 Owner 私有环境运行：

```bash
storyforge-gold-quality import-reviewer-b \
  --input /private/path/R58_GOLD192_REVIEWER_B_RESULTS_20261102.json \
  --manifest /private/path/gold-quality-events.jsonl \
  --repo-root "$PWD"

storyforge-gold-quality reconcile-gold192 \
  --manifest /private/path/gold-quality-events.jsonl
```

导入器仅接受上述精确 SHA、Schema、状态、192 条数量、决策计数、唯一 blind ID / target SHA、完整六维分数、severe_flags 和 evidence_summary。原始 evidence_summary 只写入权限受限的私有 Manifest；SAFE 导入回执不输出逐案 ID、目标哈希、分数或文本。相同来源重复运行是幂等的；部分导入会 HOLD。

Reviewer A 与 B 的 blind ID 属于各自 reviewer 的局部编号，**不得假设相同**。统一仲裁按 target SHA-256 配对。所有缺少当前 canonical source SHA 的旧 Reviewer B 事件被标记为 superseded/unpinned 并排除在当前分歧计算之外；旧事件不会覆盖新版，也不会被解释成当前审核结论。

新版文件的 12 HOLD、2 REJECT 均原样保留。任何历史 REJECT 仍需仲裁；Reviewer B 的 PASS 不会清除 Reviewer A 的 REJECT，也不直接产生 Quality-v1 准入。RB-0001 的年龄字段冲突属于额外 Owner 核对项，不因其 PASS 自动关闭。

此流程只导入和核对审核证据；不验证角色卡在目标时点的生效版本，不完成世界身份/别名语义核验，不完成 Reviewer 独立性认证，不执行训练授权。


## 只读历史上下文恢复核心（R59）

共享实现：`src/storyforge_gold_quality/history_recovery.py`。它只接收已验证 locator 和数据库 cursor，不负责 DSN、连接、文件写入、私有权限或质量准入。项目适配器必须自行验证输入 pin、限定查询范围、建立只读事务，并输出不含私人字段的 SAFE 回执。

- Session lineage 按 `parent_session_id` 递归恢复，检测循环、缺失祖先和最大深度。Fork/rewind 会把继承消息复制到子 Session；历史消息只从目标所在的子 Session 读取一次，父 Session 仅用于 lineage 证明。`forked_from_turn` 是 story-turn 编号，不是消息表物理 `turn_index`，不得直接作为父消息过滤边界。
- 目标 Assistant 必须在指定 story/session/turn 唯一存在，正文 SHA256 精确匹配且 `status=completed`。
- 历史消息必须 `created_at < target.created_at`、位于对应 Session turn cutoff 内且 `status=completed`；不包含 system/developer 内容，不截断，末条必须是 User。
- `memory_summary`、`recent_summary`、`rolling_outline` 仅在子 Session `updated_at` 严格早于目标时点、story-turn cutoff 和物理消息索引 cutoff 均验证通过时使用。`last_summary_turn` / `last_extract_turn` 是 story-turn；`summary_*_end_index` 是物理 `turn_index`。数据库虽有 `last_summary_turn * 2` 旧兼容回退，但质量恢复门禁不接受空的 source/text/legacy 物理索引；只有显式覆盖索引完整且不越界时才使用摘要。dependency 索引可为空，非空时必须不越界。
- `story_content_versions` 只接受 `source_updated_at` 和 `archived_at` 均早于目标的最新版本；`story_admin_versions` 只接受 `created_at` 和 `updated_at` 均早于目标的记录。没有版本时明确报告，不回退到当前 `user_stories` 快照。
- 故事卡版本不等于历史 Provider System Prompt；所有适配器必须保持 `historical_system_prompt_verified=false`，不得将卡片快照伪装成生产 Prompt。
- Volume memory 暂不自动纳入；若未来接入，必须单独定义生成时间、覆盖 turn、stale 状态与分叉继承规则。

Strict28 的输入 pin、字段映射、CLI、SAFE Schema 和 Owner 本机复现步骤见 [R59 Strict28 历史上下文恢复](../R59_STRICT28_HISTORY_RECOVERY_CN.md)。该适配器只为后续 Quality-v1 SOURCE / STRUCTURE 门禁提供证据，`quality_v1_admitted=0`，不授权训练或 GPU。
