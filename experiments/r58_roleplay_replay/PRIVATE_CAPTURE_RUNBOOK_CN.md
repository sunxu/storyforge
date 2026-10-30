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
