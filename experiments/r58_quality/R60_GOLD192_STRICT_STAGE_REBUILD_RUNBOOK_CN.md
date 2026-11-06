# R60 Gold192 Strict Stage 重建与 Owner Evidence 接续 Runbook

日期：2026-11-07  
适用分支：r60/gold72-disagreement-reviewer-c  
起始代码基线：7dce3e60de50f08de91b2aa493f1a50dae7e3ace

本 Runbook 是 R60_GOLD192_INPUT_LINEAGE_FINDINGS_CN.md 的执行续篇。只处理原始 priority72 Source Context 的严格 Stage 重建、5 条 READY 的 Owner Evidence 工作副本和 Preflight。不会自动运行 Review Bind 或训练。

## 0. 已确认输入，不要重复查找

Owner Mac 私有根目录：

$PRIVATE="$HOME/.local/share/storyforge/r59/private"

已确认的原始输入：
- Source Context：$PRIVATE/r59-source-priority72-20261103/R59_SOURCE_CONTEXT_PRIVATE.jsonl
- 历史严格 Stage：$PRIVATE/source-staging-priority72-20261103/GOLD_SOURCE_STAGING_PRIVATE.jsonl
- 历史严格 Stage SAFE：$PRIVATE/source-staging-priority72-20261103/GOLD_SOURCE_STAGING_SAFE.json

历史严格 Stage 已经证明：原始 Source Context 72 行、严格 READY 5、结构 HOLD 67；Stage SAFE 的 staged-file pin 匹配实际 JSONL；Source Context pin 匹配 priority72 Source Context。

**不得使用** source-staging-suffix72-20261104-v1 作为本次 strict Stage 的输入或结果。它是历史后缀投影 Stage，72 READY 不等于完整原始历史通过严格检查。

## 1. 同步文档与固定代码

~~~bash
set -euo pipefail
cd /Users/keedle/workspace/storyforge-r60-ledger-diagnostics
git pull --ff-only origin r60/gold72-disagreement-reviewer-c
test "$(git rev-parse HEAD)" = "7dce3e60de50f08de91b2aa493f1a50dae7e3ace"
test -z "$(git status --porcelain)"

ruff check experiments/r58_quality/gold_source_context_stage.py experiments/r58_quality/r59_history_structure_diagnostic.py experiments/r58_quality/r59_owner_evidence_preflight.py experiments/r58_quality/r59_staging_receipt.py experiments/r58_quality/r59_owner_evidence_template.py experiments/r58_quality/r59_owner_evidence_autolink.py

python -m unittest discover -s experiments/r58_quality -p 'test_gold_source_context_stage.py' -v
python -m unittest discover -s experiments/r58_quality -p 'test_r59_owner_evidence_preflight.py' -v
python -m unittest discover -s experiments/r58_quality -p 'test_r59_staging_receipt.py' -v
python -m unittest discover -s experiments/r58_quality -p 'test_r59_owner_evidence_template.py' -v
python -m unittest discover -s experiments/r58_quality -p 'test_r59_owner_evidence_autolink.py' -v
~~~

任何 Ruff / test 失败，停止并回传错误类别；不绕过测试，不启动 Stage。

## 2. 创建全新私有执行目录

~~~bash
umask 077
PRIVATE="$HOME/.local/share/storyforge/r59/private"
SOURCE="$PRIVATE/r59-source-priority72-20261103/R59_SOURCE_CONTEXT_PRIVATE.jsonl"
OLD="$PRIVATE/source-staging-priority72-20261103"
RUNROOT="$PRIVATE/quality-v1/r60-strict-rebuild-20261107-v1"

test -f "$SOURCE"
test -f "$OLD/GOLD_SOURCE_STAGING_PRIVATE.jsonl"
test -f "$OLD/GOLD_SOURCE_STAGING_SAFE.json"
test ! -e "$RUNROOT"
mkdir -m 700 "$RUNROOT"

PROMPT="$RUNROOT/APPROVED_SYSTEM_PROMPT_PRIVATE.txt"
STAGE="$RUNROOT/strict-stage"
TEMPLATE="$RUNROOT/owner-template"
AUTOLINK="$RUNROOT/owner-autolink"
~~~

RUNROOT 必须是 0700，且位于 Git worktree 外；所有输入文件必须为 regular、非 symlink、0600、nlink=1。不要复用已存在目录。

## 3. 从历史严格 Stage 还原相同 System Prompt 字节（仅本机）

历史严格 Stage 的 SAFE receipt 固定了当时使用的 system_prompt_sha256。从其 READY 行提取 system 消息，验证历史 Stage JSONL pin、Source Context pin、72/5/67 计数、READY 行 system 内容一致，以及提取内容 SHA 与 receipt 的 system_prompt_sha256 相同。

以下命令只把 system prompt 写到本机 0600 文件，并通过 shell 变量传递 SHA；不向终端打印 prompt 或 SHA：

~~~bash
SYSTEM_SHA="$(python3 - "$SOURCE" "$OLD/GOLD_SOURCE_STAGING_PRIVATE.jsonl" "$OLD/GOLD_SOURCE_STAGING_SAFE.json" "$PROMPT" <<'PY'
import hashlib, json, os, stat, sys
from pathlib import Path
source, staged, receipt_path, prompt = map(Path, sys.argv[1:])

def private(p):
    if p.is_symlink() or not p.is_file():
        raise SystemExit("HOLD_INPUT_NOT_REGULAR")
    s = p.stat()
    if stat.S_IMODE(s.st_mode) != 0o600 or s.st_nlink != 1:
        raise SystemExit("HOLD_INPUT_PERMISSION")
    return p.read_bytes()

src, raw, receipt_raw = private(source), private(staged), private(receipt_path)
receipt = json.loads(receipt_raw)
sha = lambda b: hashlib.sha256(b).hexdigest()

if receipt.get("schema") != "storyforge-gold-quality-supabase-source-stage-safe-v1":
    raise SystemExit("HOLD_OLD_RECEIPT_SCHEMA")
if receipt.get("status") != "GOLD_SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING":
    raise SystemExit("HOLD_OLD_RECEIPT_STATUS")
if receipt.get("source_context_file_sha256") != sha(src):
    raise SystemExit("HOLD_SOURCE_PIN")
if receipt.get("staged_file_sha256") != sha(raw):
    raise SystemExit("HOLD_STAGE_PIN")
if (receipt.get("source_rows"), receipt.get("context_staged"), receipt.get("context_structure_hold")) != (72, 5, 67):
    raise SystemExit("HOLD_OLD_RECEIPT_COUNTS")

rows = [json.loads(x) for x in raw.splitlines() if x.strip()]
ready = [x for x in rows if x.get("schema") == "storyforge-quality-v1-source-staging-private-v1" and x.get("status") == "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING"]
held = [x for x in rows if x.get("status") == "SOURCE_STRUCTURE_HOLD"]
if (len(rows), len(ready), len(held)) != (72, 5, 67):
    raise SystemExit("HOLD_OLD_JSONL_COUNTS")

systems = []
for row in ready:
    msgs = row.get("messages")
    if not isinstance(msgs, list) or not msgs or not isinstance(msgs[0], dict) or msgs[0].get("role") != "system":
        raise SystemExit("HOLD_SYSTEM_MESSAGE_MISSING")
    systems.append(msgs[0].get("content"))
if not systems or any(not isinstance(x, str) or not x for x in systems) or len(set(systems)) != 1:
    raise SystemExit("HOLD_SYSTEM_PROMPT_INCONSISTENT")

prompt_bytes = systems[0].encode("utf-8")
prompt_sha = sha(prompt_bytes)
if prompt_sha != receipt.get("system_prompt_sha256"):
    raise SystemExit("HOLD_SYSTEM_PROMPT_PIN")

fd = os.open(prompt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "wb") as f:
    f.write(prompt_bytes)
    f.flush()
    os.fsync(f.fileno())
print(prompt_sha)
PY
)"
test -n "$SYSTEM_SHA"
test -f "$PROMPT"
~~~

这一步证明还原字节与历史 Stage receipt 一致；它本身不创造新的 System Prompt 审批。如果历史审批记录不能确认该 prompt 仍是本任务获批的精确版本，停止，不得仅凭 receipt 推断审批。

## 4. 重建 Strict Source Stage

~~~bash
python experiments/r58_quality/gold_source_context_stage.py --source-context-jsonl "$SOURCE" --system-prompt-file "$PROMPT" --system-sha256 "$SYSTEM_SHA" --output-dir "$STAGE" > "$RUNROOT/STRICT_STAGE_COMMAND_OUTPUT_PRIVATE.json"
~~~

CLI 输出含文件 SHA，必须保留在本机私有目录，不要复制到聊天。

Stage 完成后，使用 Python 本机只读核对：
- SAFE 的 source_context_file_sha256 等于 SOURCE 实际 SHA；
- SAFE 的 staged_file_sha256 等于新 JSONL 实际 SHA；
- 实际 JSONL 总行数 72；
- 实际 READY 5，实际 SOURCE_STRUCTURE_HOLD 67；
- receipt 的 source_rows/context_staged/context_structure_hold 分别为 72/5/67；
- quality_v1_admitted=0、training_authorized=false、gpu_started=false、r50_accessed=false。

任意一项不匹配立即 HOLD。只回传聚合字段，不回传 SHA 或私有文件。

## 5. 为 Strict READY 子集建立新 Owner Evidence 模板

旧 72 行 Owner Evidence 的 staged pin 属于 suffix72 文件，不能直接复用。必须针对新 strict Stage 重新生成只有 5 个 READY 案例的模板：

~~~bash
python experiments/r58_quality/r59_owner_evidence_template.py --staged-jsonl "$STAGE/GOLD_SOURCE_STAGING_PRIVATE.jsonl" --staging-safe "$STAGE/GOLD_SOURCE_STAGING_SAFE.json" --output-dir "$TEMPLATE" > "$RUNROOT/OWNER_TEMPLATE_COMMAND_OUTPUT_PRIVATE.json"
~~~

模板必须是 5 rows；Owner attestations、evidence、world/split/source version 字段均为 null。模板不是审核证据或审批。

## 6. 仅自动关联冻结 A/B 与 Packet 定位符

已知历史候选路径（Owner 本机先检查文件是否存在；不要将路径发到聊天）：

~~~bash
PACKETS="$PRIVATE/GOLD192_STORY_REVIEW_PACKETS_PRIVATE.jsonl"
A="$HOME/.local/share/storyforge/r58/private/R58_GOLD192_REVIEWER_A_RESULTS_20261102.json"
B="$HOME/.local/share/storyforge/r58/private/R58_GOLD192_REVIEWER_B_RESULTS_20261102.json"
EX="$PRIVATE/quality-v1/QUALITY_V1_EXCLUDED_CASES.jsonl"
~~~

自动关联程序会自行验证冻结 Packet/A/B 的代码内 SHA pin 和覆盖率；任何输入不匹配即 HOLD：

~~~bash
python experiments/r58_quality/r59_owner_evidence_autolink.py --packet-jsonl "$PACKETS" --staged-jsonl "$STAGE/GOLD_SOURCE_STAGING_PRIVATE.jsonl" --reviewer-a "$A" --reviewer-b "$B" --owner-template-jsonl "$TEMPLATE/OWNER_CASE_EVIDENCE_TEMPLATE_PRIVATE.jsonl" --output-dir "$AUTOLINK" > "$RUNROOT/OWNER_AUTOLINK_COMMAND_OUTPUT_PRIVATE.json"
~~~

只有冻结输入完整且严格 5 个候选全部精确关联，才会得到 5 个 locator-linked rows。此步骤不创建 Owner 判断、不证明 Reviewer independence、不证明 source-version temporal validity、不证明 protected-set completeness。

## 7. Owner 本人补真实证据；Preflight 后才允许 Binder

把自动关联结果复制成独立工作副本，绝不覆盖自动关联原件：

~~~bash
OWNER_WORK="$RUNROOT/OWNER_CASE_EVIDENCE_OWNER_REVIEWED_PRIVATE.jsonl"
test ! -e "$OWNER_WORK"
cp "$AUTOLINK/OWNER_CASE_EVIDENCE_AUTOLINKED_PRIVATE.jsonl" "$OWNER_WORK"
chmod 600 "$OWNER_WORK"
~~~

Owner 只针对这 5 个 strict READY 案例，根据真实来源逐项填写。未知字段必须保持 null，不能默认 false/true。包括：
- severe flags 三项及其 evidence ref；
- 全部正向 evidence；
- 三项负向 evidence（必须有证据确认 false）；
- 原始 Gold source version SHA（不可用 Stage/Source Context SHA 替代）；
- world graph SHA、world component、train/validation split；
- Reviewer refs 只作为 locator，不代表独立性证明。

填完后运行 Preflight：

~~~bash
python experiments/r58_quality/r59_owner_evidence_preflight.py --staged-jsonl "$STAGE/GOLD_SOURCE_STAGING_PRIVATE.jsonl" --staging-safe "$STAGE/GOLD_SOURCE_STAGING_SAFE.json" --owner-evidence-jsonl "$OWNER_WORK" > "$RUNROOT/OWNER_EVIDENCE_PREFLIGHT_SAFE.json"
~~~

本机额外核对：staged_ready=5、owner_rows=5、identity_matched=5，且所有 staged/source pins 匹配。只有 rows_with_all_required_fields_present > 0 才能进入 Review Bind。Reviewer independence 与 protected-set completeness 仍需独立证明，Preflight complete 不等于准入。

## 8. 硬停止条件

Strict Stage 不是 72/5/67；历史 System Prompt 审批无法确认；Source / Stage / receipt pin 或权限不匹配；Frozen Packet/A/B 输入 pin 不匹配；Owner 证据未知或无法追溯；Preflight READY 数不等于 Strict Stage READY；complete rows=0；Reviewer independence 或 protected-set completeness 未证明——任一条件出现均保持 HOLD，不得运行 Binder、Quality-v1 admission、tokenizer/collator 或 GPU。

## 9. 保护状态

本 Runbook 不访问 R50、不修改生产 B2、不执行 DDL/DML、不启动 GPU、不自动合并 PR。每轮只回传 SAFE 聚合字段与公开代码/CI 证据，不回传私有路径、案例 ID、故事正文、DSN、Token 或原始私有 SHA。
