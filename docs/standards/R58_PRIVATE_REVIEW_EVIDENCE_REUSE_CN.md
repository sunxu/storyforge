# R58 私人审核证据复用规范

更新：2026-11-02。状态：**通用离线 Manifest ↔ 当前任务身份核验器已实现；真实私人输入尚未在本次工具开发中读取或核验**。

## 1. 目的与非目标

工具 **experiments/r58_quality/private_review_evidence_reuse.py** 用于回答一个有限问题：**既有私人审核 Manifest 中的某个案例，是否仍然对应当前审核任务中的完全相同输入与 Gold 目标？**

它只建立历史证据与当前任务的内容身份对应关系，不执行审核，不重新解释评审结论，也不授予 Quality-v1 或训练资格。

明确非目标：

- 不访问 Grok 网页、任何模型 API、HF、GPU、数据库或 R50。
- 不读取历史 Reviewer JSON、仲裁文件或后续重审文件；它们由既有验证器与结案工具单独检查。
- 不判断评审者是否独立，不证明评审推理正确，也不证明文学质量。
- 不生成、修改、移动或删除私人输入/输出，不上传任何内容。
- 不要求当前任务数量等于历史 Manifest 数量；历史 Manifest 可以是完整任务集合中的任意子集。

## 2. 数量与范围：不得写死批次大小

- Manifest 的 cases 数量是历史证据条目数，必须大于零，但没有固定的 3、13、63、132、195 等数量要求。
- 当前任务 JSONL 可以多于、少于或恰好等于 Manifest 条目数；工具按 case_id 对齐，不按数组顺序或行号匹配。
- 默认最多读取 100,000 条记录、每个输入文件最多 128 MiB；两项均可通过 CLI 参数调整。超过限制直接 HOLD，不截断、不静默跳过。
- 当前 Gold195 的既有试点 Manifest 目前包含 3 个案例；这只是历史 Manifest 的实际大小，不是工具约束。

## 3. 身份匹配合同

每个 Manifest 案例必须包含：

- label：非空且在 Manifest 内唯一的匿名标签。
- case_id：非空且在 Manifest 内唯一的稳定案例标识。
- input_messages_sha256：完整序列化输入消息的 SHA256。
- target_sha256：Gold 目标文本 UTF-8 字节的 SHA256。
- target_text：原始目标文本；工具在内存中重新计算 SHA256，不输出文本。

每个当前任务必须包含：

- case_id、messages、target_text。
- input_messages_sha256、target_sha256。
- 当前默认任务 Schema 为 r58_gold195_six_dimension_review_task_private_v1；可用 --task-schema 显式指定其他受同合同约束的任务 Schema。

输入消息哈希采用 UTF-8 JSON：ensure_ascii=False、sort_keys=True、紧凑分隔符 (',', ':'), allow_nan=False。工具重新计算当前 messages 与 target_text 的 SHA256，不能只相信 JSON 中声明的哈希。

匹配键为三元组：

**case_id + input_messages_sha256 + target_sha256**

只有三项完全一致才是 EXACT_MATCH。不使用数组索引、匿名标签、文件名、顺序、模糊文本相似度或单独的 case_id 作为复用依据。

## 4. SAFE 状态与失败码

逐案例状态只输出聚合计数，不输出案例 ID、label、UUID、文本或 SHA256：

| 状态 | 含义 | 处理 |
|---|---|---|
| EXACT_MATCH | case_id、完整输入哈希、目标哈希完全一致 | 可作为历史证据复用候选，仍需既有审核输出验证 |
| CASE_ID_NOT_FOUND | 历史 case_id 不在当前任务中 | 该案例 HOLD |
| INPUT_MESSAGES_HASH_MISMATCH | 输入消息改变 | 该案例 HOLD，不复用旧结论 |
| TARGET_HASH_MISMATCH | Gold 目标改变 | 该案例 HOLD，不复用旧结论 |
| INPUT_AND_TARGET_HASH_MISMATCH | 输入与目标均改变 | 该案例 HOLD |

顶层状态：

- EXACT_REUSE_MATCH__NO_QUALITY_ADMISSION：Manifest 中所有案例均精确匹配。
- PARTIAL_REUSE_MATCH__MISMATCHES_HOLD：部分精确匹配；精确案例保留为复用候选，其余案例逐案 HOLD。
- NO_EXACT_REUSE_MATCH__HOLD：没有精确匹配。
- PRIVATE_REUSE_INPUT_INVALID__HOLD：输入 Schema、字段、权限、哈希、重复标识或文件边界无效。
- PRIVATE_REUSE_IO_ERROR__HOLD：私人文件读取失败。

固定 reason_code 包括：

- MANIFEST_SCHEMA_MISMATCH、MANIFEST_APPROVAL_STATE_INVALID、MANIFEST_CASE_COLLECTION_INVALID
- MANIFEST_CASE_ID_INVALID、MANIFEST_CASE_ID_DUPLICATE、MANIFEST_LABEL_INVALID_OR_DUPLICATE
- MANIFEST_DIGEST_INVALID、MANIFEST_TARGET_TEXT_INVALID、MANIFEST_TARGET_DIGEST_MISMATCH
- TASK_SCHEMA_MISMATCH、TASK_CASE_ID_INVALID、TASK_CASE_ID_DUPLICATE
- TASK_CONTENT_SHAPE_INVALID、TASK_DIGEST_INVALID、TASK_MESSAGES_NOT_CANONICAL_JSON
- TASK_INPUT_DIGEST_MISMATCH、TASK_TARGET_DIGEST_MISMATCH
- TASK_ALREADY_HAS_REVIEW_RESULTS、TASK_REVIEW_STATUS_NOT_UNREVIEWED
- TASK_QUALITY_ADMISSION_STATE_INVALID、TASK_TRAINING_AUTHORIZATION_STATE_INVALID
- JSON_DUPLICATE_KEY、TASK_JSONL_INVALID、TASKS_NOT_UTF8
- PRIVATE_FILE_PATH_INVALID、PRIVATE_FILE_INSIDE_REPOSITORY、PRIVATE_PARENT_INVALID
- PRIVATE_PARENT_PERMISSIONS_INVALID、PRIVATE_FILE_PERMISSIONS_OR_SIZE_INVALID
- PRIVATE_FILE_CHANGED_DURING_READ、PRIVATE_FILE_SIZE_CHANGED_DURING_READ
- INPUT_FILES_MUST_BE_DISTINCT、TASK_RECORD_LIMIT_EXCEEDED、LIMIT_ARGUMENT_INVALID

异常只返回固定原因码，不打印异常文本或 traceback。

## 5. 私人目录、迁移记录与文件安全

### 5.1 R58 统一私人目录

用户确认，R58 私人材料统一根目录为：

```text
$HOME/.local/share/storyforge/r58/
```

迁移约定为 `mv -n`、保留文件名和目录结构、不覆盖已有文件；目录权限 0700，私人文件权限 0600。旧 `~/storyforge-review-private` 是迁移前目录，不再作为正常工作目录或静默 fallback。

**Gold195 六维审核任务路径状态：HOLD / 尚未定位。**

历史会话记录的任务生成输出路径是：

```text
$HOME/storyforge-review-private/gold195-review-tasks-v1.jsonl
```

当时 SAFE 输出报告已准备 195 条任务、输出权限 0600。该记录证明任务曾按此路径写出，不证明它后来已迁移。2026-11-02 用户实际检查新目录下的 `$HOME/.local/share/storyforge/r58/gold195-review-tasks-v1.jsonl`，系统返回 `No such file or directory`。因此不得再把这个新路径写成已确认存在的文件，也不得仅因路径缺失就重新生成或覆盖审核任务。

**Grok Web Pilot Manifest 路径状态：预期路径，未验证存在。**

历史生成命令的输出目录为 `$HOME/storyforge-review-private/grok-web-pilot-v1/`，Manifest 文件名为 `review-manifest.private.json`。按目录迁移时保留结构的约定，其预期新路径是：

```text
$HOME/.local/share/storyforge/r58/grok-web-pilot-v1/review-manifest.private.json
```

但历史记录没有提供该文件迁移后的独立存在性检查；不得将预期路径表述为已验证路径。

历史伴随材料还包括 `gold195-card-snapshots-v1.json`、`gold195-card-gold-review-v1.jsonl`、`gold195-review-tasks-user-first-v1.jsonl`、`case02-final-disposition-v1.json`，以及 `grok-web-pilot-v1/`、`grok-web-followup-v1/` 子目录中的初轮审核、仲裁和重审材料。该清单只作为历史文件名线索，不证明每个文件都已迁移或当前存在。

### 5.2 只读定位步骤

在执行身份复用核验前，先只读定位文件，不移动、不改名、不生成、不覆盖：

~~~bash
PRIVATE_R58_ROOT="$HOME/.local/share/storyforge/r58"
OLD_PRIVATE_ROOT="$HOME/storyforge-review-private"

echo "=== R58 unified root: Gold195 task ==="
find "$PRIVATE_R58_ROOT" -type f -name 'gold195-review-tasks-v1.jsonl' -print
find "$PRIVATE_R58_ROOT" -type f -iname '*review*tasks*.jsonl' -print

echo "=== R58 unified root: Grok Pilot Manifest ==="
find "$PRIVATE_R58_ROOT" -type f -path '*/grok-web-pilot-v1/review-manifest.private.json' -print

if [ -d "$OLD_PRIVATE_ROOT" ]; then
  echo "=== retired root: migration reconciliation only ==="
  find "$OLD_PRIVATE_ROOT" -type f -name 'gold195-review-tasks-v1.jsonl' -print
  find "$OLD_PRIVATE_ROOT" -type f -iname '*review*tasks*.jsonl' -print
  find "$OLD_PRIVATE_ROOT" -type f -path '*/grok-web-pilot-v1/review-manifest.private.json' -print
fi
~~~

解释结果时遵守以下规则：

- 只在统一根目录找到唯一任务文件：记录实际路径，再检查普通文件、权限 0600、硬链接数 1、父目录权限及仓库外边界。
- 只在旧根目录找到：保持 HOLD；这只是迁移遗漏线索，不得静默从旧目录读取或自动搬动。
- 找到多个候选、没有候选、文件权限异常或路径存在符号链接：保持 HOLD，先由 Owner 确认正确文件。
- 不得根据文件名相似、195 行数量或历史 SAFE 摘要推断文件内容相同；必须对实际文件运行身份核验。
- 任务文件未定位前，不运行私人证据复用核验器，也不重新生成任务。

### 5.3 文件安全

- Manifest 和任务 JSONL 必须使用绝对路径，位于 Git 仓库之外。
- 文件必须为普通文件、权限严格为 0600、硬链接数为 1；父目录不得为符号链接，且 group/other 不得有任何权限（通常 0700）。
- 使用 O_NOFOLLOW（平台支持时）打开文件，并比对打开前后的设备号/inode，拒绝读取期间被替换的文件。
- 不写任何文件。SAFE 输出只包含数量、固定状态码及布尔边界，不包含私有路径、case_id、story UUID、文本、哈希或评审内容。
- 文件内容不进入 GitHub Actions、Git、普通日志或聊天；测试只使用合成 canary。

## 6. 使用方式

只有在第 5.2 节定位出唯一任务文件和唯一 Manifest，并完成权限检查后，才执行：

~~~bash
PRIVATE_MANIFEST="/absolute/path/confirmed/review-manifest.private.json"
PRIVATE_TASKS="/absolute/path/confirmed/gold195-review-tasks-v1.jsonl"

test -f "$PRIVATE_MANIFEST" && test -f "$PRIVATE_TASKS" || {
  echo "HOLD: private evidence input missing"
  exit 1
}

python3 experiments/r58_quality/private_review_evidence_reuse.py \
  --repo-root "$PWD" \
  --private-manifest "$PRIVATE_MANIFEST" \
  --private-tasks "$PRIVATE_TASKS"
~~~

以上占位路径必须替换为第 5.2 节定位并由 Owner 确认的实际绝对路径，不得直接复制执行。不得回退旧目录，不得猜测替代文件名。容量限制可通过 `--max-file-bytes` 与 `--max-records` 调整，不能用增大限制来绕过异常文件或不完整输入。

退出码：

- 0：Manifest 所有案例精确匹配；仅表示输入身份相同。
- 42：输入无效或至少一个历史案例未精确匹配；SAFE JSON 仍会列出可复用精确匹配数和各类 HOLD 数。

## 7. 后续审核证据复用

精确匹配后，仍须按历史工作流执行：

1. 使用 gold195_grok_web_validate.py 验证初轮 Reviewer JSON 与历史 Manifest 的目标引用关系。
2. 如存在定向复审，使用 gold195_grok_web_followup_validate.py 核验仲裁与重审输出。
3. 使用 gold195_grok_web_pilot_closure.py 核验既有结案条件和未决严重问题；不得通过投票或重复复审抹除 HOLD。
4. 对匹配成功的案例，只能说“历史评审输入身份匹配，历史输出可进入既有验证链”；不能说新的文学质量已获独立证明。
5. 任何输入或目标哈希变化，必须对该案例重新审核；不得复用旧评审结果。

历史审核结论、程序结构验证、独立语义判断、世界组件隔离、Quality-v1 准入和 GPU/训练授权始终是不同门禁。

## 8. 合成回归测试要求

当前 14 项合成测试覆盖可变数量、精确/部分/无匹配、输入/目标哈希变化、重复标识、重复 JSON key、哈希重算、审核/准入状态、文件权限与仓库边界、SAFE 隐私输出。

以下边界仍列为后续测试合同，不得误报为当前已覆盖：符号链接输入、硬链接输入、父目录权限、文件大小上限、并发替换/读取竞态、Manifest Schema 与任务 Schema 的完整负例矩阵。

测试不访问生产数据库、Grok、HF、GPU、R50 或真实私人文件。
