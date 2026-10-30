# R58 Priority3 — HF 私有隔离包捕获操作说明（暂不执行）

本文件配合 `PRIVATE_PRIORITY3_QUARANTINE_EXPORT_TEMPLATE.sql`，为 StoryForge 的 RolePlay→SFT 真实端到端工作流准备。**此工具不属于 Skill v0.1 正式实现，不是数据集准入，也不是对付费 HF Job 的授权。**

## 一、严格边界

1. 查询仅在 HF **私有**工作区/已获授权的受控环境中执行，使用专用 PostgreSQL **只读账号**。生产 Supabase 不能被写入、锁表、扩大超时或做全库扫描。
2. SQL **会返回故事卡、用户原文、Assistant 原文、检查点和 ID**。因此绝对**不要**通过 ChatGPT Supabase 连接执行该私有 SQL，不将结果粘贴进聊天、GitHub、PR 日志或公开输出。
3. 只允许写入已设置权限 `0700` 的私有目录，数据文件 `0600`，关闭 shell xtrace 与训练日志回显。凭据通过已有秘密管理传递，不写入任何文本文件、命令行 URL 或 Git 提交。
4. 在真实数据冻结之前先与 R50 和其他保护集仅做**世界 ID/语义别名/曝光索引**比对，不读取保护集原文；不匹配就 HOLD。
5. 三条隔离包只用于 SOURCE/REPLAY 验证，**不能**在没有双 Reviewer、独立世界划分、Owner 批次批准和 HF CPU Collator 通过前训练。

## 二、导出前提

- 访问源码 commit `sunxu/RolePlay@e9fe29c42434caeb0bac5acc91845ab4741ecb2b`；仍需查明实际目标时点部署版本。
- 仓库路径 `experiments/r58_roleplay_replay/PRIVATE_PRIORITY3_QUARANTINE_EXPORT_TEMPLATE.sql`，源码本身无密钥和私有记录。
- 单个 SELECT 使用一个 PostgreSQL statement MVCC snapshot。**逻辑选择由当时生产库状态驱动，不等于真正固定物理案例**；第一次完整导出后必须保存源记录/来源哈希，此后的重试不能悄悄选新消息。
- 查询包含非匿名 ID、内容及仅按时间邻近而非精确请求关联的 metrics，务必对 metrics 保留 `untrusted_nearby_metric` 标签。

## 三、私有环境执行（由 Owner 单独批准的执行环境）

在 HF 私有环境安装有 `psql` 的机器执行，数据库口令须通过环境自带 secret store/受限 `.pgpass` 提供。**下面只提供执行说明，本轮未启动机器或连接。**

```bash
set -euo pipefail
set +x
umask 077

# 工作目录必须是私有目录，不能在公开仓库 checkout 内写入输出
PRIVATE_DIR=/workspace/storyforge-r58-private/replay-priority3
mkdir -p -m 700 "$PRIVATE_DIR"
chmod 700 "$PRIVATE_DIR"

SQL_PATH=experiments/r58_roleplay_replay/PRIVATE_PRIORITY3_QUARANTINE_EXPORT_TEMPLATE.sql
DEST="$PRIVATE_DIR/priority3_source_quarantine.jsonl"
test ! -e "$DEST" || { echo "HOLD: output exists; refusing overwrite" >&2; exit 42; }

TMP="$(mktemp "$PRIVATE_DIR/.priority3.XXXXXXXX")"
trap 'rm -f "$TMP"' EXIT
chmod 600 "$TMP"

# PGHOST/PGDATABASE/PGUSER/PGSSLMODE + 安全提供的身份凭据由运行环境设置
PGOPTIONS="-c default_transaction_read_only=on" \
  psql -X -qAt -v ON_ERROR_STOP=1 -f "$SQL_PATH" > "$TMP"

# 标准库只检查结构，不向终端打印正文或 ID
python - "$TMP" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
rows = [json.loads(s) for s in p.read_text('utf-8').splitlines() if s.strip()]
expected = {'AUTHOR', 'CURRENT_PUBLIC', 'OLD_PUBLIC'}
assert len(rows) == 3, 'HOLD: expected exactly 3 cases'
cohorts = {r['case']['cohort'] for r in rows}
assert cohorts == expected, 'HOLD: missing/duplicate source route'
assert len({r['case']['target_message_id'] for r in rows}) == 3
assert len({r['case']['story_id'] for r in rows}) == 3
for r in rows:
    assert r['status'] == 'NOT_ADMITTED_NOT_BYTE_EXACT__REPLAY_PENDING'
    assert isinstance(r['historical_approved_story']['v2_data'], dict)
    assert isinstance(r['prior_checkpoint']['snapshot'], dict)
    assert len(r['history24']) == 24
    assert all(x['status'] == 'completed' for x in r['history24'])
    assert r['structural_checks']['post_target_ledger_events'] == 0
    assert r['target']['content']
PY

# 0600 private folder only; never commit/echo the bytes.
# 不使用 mv -n 的不可靠成功码：私有目录禁并行写入
test ! -e "$DEST" || exit 42
mv "$TMP" "$DEST"
trap - EXIT
chmod 600 "$DEST"
sha256sum "$DEST" > "$PRIVATE_DIR/priority3_source_quarantine.sha256.private"
chmod 600 "$PRIVATE_DIR/priority3_source_quarantine.sha256.private"
```

**注意**：上例为执行手册，不是本轮运行成功证据。真实生产执行还应加进程独占锁和检查输入 SQL Git Blob SHA，以避免并发或源版本漂移。

## 四、隔离包校验与后续复原

导出后在 HF 私有环境保留每条案例的 `source_submission_id`、`source_content_revision`、批准卡、最近检查点、前置消息、目标消息以及文件级 SHA256。转换到 SFT 输入前还必须核验：

- 源文件的每条逻辑记录哈希和所有审计/证据标识。
- 故事世界别名是否与 R46/R54/R55 训练、验证或 R50 保护世界重叠。
- 服务端**实际部署源码**、运行配置、原始请求 locale、选择模型、base mode、输出模式、补充/重生成参数。
- 按真实摘要窗口、结构化清理、反复读与用户指令注入组装 11 条历史。
- 历史 checkpoint 与逐轮 event runtime 连续性，RAG/事实/角色状态等异步依赖及其超时降级。
- 原始请求字节或可信哈希；不存在时明确降级为 `RECONSTRUCTED_WITH_EVIDENCE`，而不是自称 `BYTE_EXACT_PASS`。

如 3 条无法同时完成完整上下文恢复，应保留 HOLD 的失败原因并在初版 Skill 的未来修订版本中处理。**Skill v0.1 本轮不改，Train/Val 正式准入仍为零。**

## 五、2026-10-30 捕获器补充（优先于第三节的 Shell 手工保存）

**新捕获入口：** `experiments/r58_roleplay_replay/capture_priority3.py`；合成单元测试：`test_capture_priority3.py`。两者不访问数据库、网络或模型，只处理标准输入的 JSONL 字节。

相比第三节的手工校验方法，新入口还逐案检查：
- 来源路径恰好各 1 条、3 个物理 story_id/message_id 都不同；
- approved submission 快照完整、`approval_at < target_created_at`；
- checkpoint 快照完整、检查点创建时间与逻辑轮次早于目标；
- 历史 24 条按物理序号严格递增、全部 completed 且创建时间不晚于目标；
- 从读入的**原始 JSONL 字节**计算 SHA256，私有 manifest 另存来源卡、checkpoint、history24 与 target 的逐案内容指纹；
- 拒绝覆盖已存在快照、符号链接、非 `0700` 的目标父目录，文件按 `0600` 创建；`CAPTURE_COMPLETE` 最后写入。中断留下的不完整目录不可继续复用；
- 哈希与历史数据保留在 `manifest.private.json`，因为清单包含真实 story/message/submission ID，**不得提交 GitHub 或复制到对话**。

在有明确执行授权的 HF 私有环境，推荐命令（**本次未执行**）：

```bash
set -euo pipefail
set +x
umask 077
PRIVATE_PARENT=/workspace/storyforge-r58-private
mkdir -p -m 700 "$PRIVATE_PARENT"
chmod 700 "$PRIVATE_PARENT"

python -m unittest discover -s experiments/r58_roleplay_replay -p 'test_capture_priority3.py' -v

# 防止重入：一次运行只可使用从未存在的唯一目录名。
# Postgres 身份凭据由 HF Secret / 已授权安全配置提供，禁止写入本仓库。
PGOPTIONS='-c default_transaction_read_only=on' \
  psql -X -qAt -v ON_ERROR_STOP=1 \
  -f experiments/r58_roleplay_replay/PRIVATE_PRIORITY3_QUARANTINE_EXPORT_TEMPLATE.sql \
  | python experiments/r58_roleplay_replay/capture_priority3.py \
      --private-parent "$PRIVATE_PARENT" \
      --name "priority3_source_20261030_first_capture"
```

必须同时满足：**数据库端只读 + `psql` 成功退出 + 捕获器返回 0 + `CAPTURE_COMPLETE` 存在 + 私有 manifest/source SHA 一致**。若任何一步失败，保留 HOLD，不宣称完成。首次捕获后禁止用相同时间种子从动态数据库“补跑替换”原始物理案例。

本轮仅对 SQL 做 `EXPLAIN` 并在隔离的本地测试环境跑合成测试。**没有启动 HF、没有执行私有导出 SELECT，也没有物理案例冻结。**

## 六、CPU-only HF Job 一键执行入口

新增 `run_priority3_cpu_capture.sh`，在独立 HF CPU Job 内运行：检查只读数据库环境变量、拒绝 `postgres` 管理员账户、合成测试、Postgres 连接的 `transaction_read_only=on`、目标路径权限，然后通过 `psql | capture_priority3.py` 进行一次受控捕获，最后复核私有文件级 SHA256。**不调用模型、不启动训练、不访问 R50。**

Mac 上的 Hugging Face CLI 任务应通过 `-v ./experiments/r58_roleplay_replay:/app/r58:ro` 只上传此代码目录，另挂载 `hf://buckets/adradar/storyforge-training:/workspace` 写入私有目标；`PGPASSWORD` 使用 `-s PGPASSWORD` 以 HF Job 加密 secrets 注入，严禁用 `-e PGPASSWORD=...`。其他 PGHOST/PGPORT/PGDATABASE/PGUSER 可使用普通 `-e`。

示例远端容器命令：`python:3.12-slim bash /app/r58/run_priority3_cpu_capture.sh`（此 Shell 会在需要时安装 postgresql-client）。**旧 HF Job 方案仅供未来自愿迁移**；2026-10-30 实际已由 Owner 在 Mac 本地完成第一次私有捕获，HF Jobs 因余额不足未提交。禁止重跑导出替换该固定来源包。

Job 必须有专用只读 Postgres 账户，且可读取本 SQL 关联的表及审核/账本记录。HF Storage Bucket 必须是 Owner 的私有 Bucket；FUSE 权限不满足时 fail-closed，不要删掉安全检查绕过。完整 shell 命令在 ChatGPT 的操作指引中提供。

预期 stdout 只出现安全摘要 `PRIVATE_CAPTURE_COMPLETE_NOT_TRAIN_ADMITTED` 和 `R58_PRIVATE_SOURCE_CAPTURE_VERIFIED`；若出现 HOLD/SQL 超时/私有路径不可 chmod，则停止，**不要复制包含原始 SQL 或输出数据的完整日志到聊天**。

## 七、Owner 实际本机捕获已通过（2026-10-30）及下一步复核

Owner 已报告实际私有捕获 `records=3`、`PRIVATE_CAPTURE_COMPLETE_NOT_TRAIN_ADMITTED`，并报告 `R58_SOURCE_CAPTURE: PASS`、`SHA256_VERIFICATION: PASS`、`TRAINING_ADMISSION: HOLD`。**证据等级为 OWNER_REPORTED**；原始文件与私有哈希未被复制进聊天或 GitHub。

下一步**不需要数据库连接、不需要重新捕获**：在 Mac 本地对已保存的隔离目录运行新的离线复核工具，逐条重算 12 个内容指纹：

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only

python3 -m unittest discover -s experiments/r58_roleplay_replay \
  -p 'test_verify_priority3_private.py' -v

python3 experiments/r58_roleplay_replay/verify_priority3_private.py \
  --private-dir "$HOME/.storyforge-r58-private/priority3_source_20261030_first_capture"
```

仅在新合成测试通过时运行第二条。预期 `status=R58_OWNER_LOCAL_PRIVATE_CAPTURE_RECHECK_PASS`、`case_fingerprints_verified=12`、`records=3`、`training_admission=HOLD`。这是二次**源包一致性**核验，不是防恶意篡改签名、实际 API 请求字节验证、世界隔离或训练批准。若失败，**不要**覆盖、重跑或修改既有原始数据，只保留 HOLD 和非敏感错误概要。

## 八、Owner 12 个逐案指纹已通过及条件性历史窗口预检（2026-10-30）

Owner 报告 `R58_OWNER_LOCAL_PRIVATE_CAPTURE_RECHECK_PASS`、`case_fingerprints_verified=12`、私有文件权限与来源 SHA256 均 PASS。私有源包已经固定，不再通过数据库重选。本助手未接触私有正文和哈希。

新离线预检：

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only

python3 -m unittest discover \
  -s experiments/r58_roleplay_replay \
  -p 'test_preflight_priority3_history.py' -v

# 仅在上述测试全部通过时执行
python3 experiments/r58_roleplay_replay/preflight_priority3_history.py \
  --private-dir "$HOME/.storyforge-r58-private/priority3_source_20261030_first_capture"
```

预检对照 pinned RolePlay 源码计算**假设正常 DB 历史路径**的消息窗口：12 条上限、基于历史检查点 `last_summary_turn` 裁剪、从首条 User 对齐；再检查 11 条消息结构、相邻事件 `after/before` 连续性与**仅时间邻近**的日志 `historyMsgCount`。它还保守提示可能受 `continue`、历史修改、结构化协议清理影响的记录。

**不能**把 `R58_CONDITIONAL_HISTORY_WINDOW_STRUCTURE_PASS` 宣布为真实 11 条原始请求字节级重建。实际当时的部署 commit、user request flags、locale、runtime prompt rollout、RAG、反复读和策略清理、最后 User 指令注入、请求 hash 仍未取得。Fail/HOLD 时不得重新运行生产数据库补选，更不得重写已固定的 `source.private.jsonl`。

当前该预检和它的 10 项新合成测试**尚未取得 Owner 运行回执**。Train/Val/Teacher 正式准入保持零、Skill v0.1 不改、PR #7 继续 Draft。

## 九、Owner 条件性 11 消息历史预检 3/3 PASS；修订版号待分类（2026-10-30）

Owner 报告 `R58_CONDITIONAL_HISTORY_WINDOW_STRUCTURE_PASS__RUNTIME_REPLAY_HOLD`：3 路来源均推导出 11 消息；附近 `historyMsgCount=11` 3/3；Reader Event after/before 2/2，Author Event 元数据缺失；三路均有 `mutated_rows_in_conditional_window=5`。真实请求字节、历史送模字节以及训练准入仍 HOLD。

从 Supabase 只读数据库函数定义确认 `mutation_revision` 会因 `status` 或 `partial_content` 变化增加，**不能据此声称五条正文被编辑**。按固定 RolePlay 源码的实际 `pruneHistoryBySummary` 使用 `v2Session.last_summary_turn`，而此离线预检用了 checkpoint 快照中相同字段；它们在目标请求时是否一致，仍缺证据。

下一步以已冻结源包为输入，不连接 Supabase：

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
python3 -m unittest discover \
  -s experiments/r58_roleplay_replay \
  -p 'test_audit_priority3_mutation_revisions.py' -v

# 仅在新测试全通过后运行
python3 experiments/r58_roleplay_replay/audit_priority3_mutation_revisions.py \
  --private-dir "$HOME/.storyforge-r58-private/priority3_source_20261030_first_capture"
```

该工具只输出每种来源的 11 条窗口中 User/Assistant 总数及 revision-positive 计数，不打印正文、ID、digest，且保留 `historical_content_unchanged=HOLD`。新增 8 项合成测试；本节撰写时尚待 Owner 执行。无论结果如何，**不要覆盖原始私有捕获或改变训练准入状态**。

## 十、Owner 修订角色审计 PASS 后的离线深度分类

Owner 报告的三组历史窗口均为 11 条，User 正修订数均为 0，Assistant 正修订数均为 5，合计 15/15 条正修订都属于 Assistant。该结果仍然**不能证明**每条修订原因只是流式完成。

新增纯离线 `profile_priority3_revision_depth.py`，把既有已冻结窗口按角色划分成 `revision_0`、`revision_1`、`revision_2_plus` 三档；不接触私有账本或网络，不打印原文、哈希和 ID：

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only

python3 -m unittest discover \
  -s experiments/r58_roleplay_replay \
  -p 'test_profile_priority3_revision_depth.py' -v && \
python3 experiments/r58_roleplay_replay/profile_priority3_revision_depth.py \
  --private-dir "$HOME/.storyforge-r58-private/priority3_source_20261030_first_capture"
```

工具附带 7 项纯合成回归测试（Owner 尚未运行，不能提前宣布 PASS）。若 15 个 Assistant 皆为 revision=1，则与一次流式最终写入相符，**仍不证明**未发生正文变化；若存在 revision >= 2 则优先追查这些消息的 Ledger 时间/操作。所有情况 `as-of` 历史原文与 provider 原始请求仍 HOLD。

单独的固定 33 条 Ledger as-of 对照是下一道**尚未完成**的门禁：只能在 Owner 授权的私有环境中以固定 ID 只读聚合执行，返回不含 ID、正文、hash 的计数。不可重新执行动态选样 SQL，也不可把私有消息列表带到 ChatGPT/GitHub。
