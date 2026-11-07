# R60 双轨 SFT：Supabase 首批 Owner 范围候选预筛

状态：`SAFE_METADATA_PILOT_IMPLEMENTED__NOT_EXECUTED_AGAINST_BUSINESS_ROWS`。

## 目的与双轨隔离

- `STRICT_GOLD_QUALITY_V1`：已有 Gold192 冻结来源及原 28 条显式 A/B 候选保持不变。输入 A/B 取证、Reviewer/Owner、世界/Protected Set/曝光必须独立通过；本轮不会将新数据库候选混入 Gold192 的冻结清单。
- `RECONSTRUCTED_CONTEXT_SFT_EXPERIMENTAL`：以**新的独立候选池**寻找具备来源和监督语义、可追溯世界的最终 Assistant 回复；用 `RECONSTRUCTED_NOT_ACTUAL_SENT` 标记未经证明的输入。需要单独的 dataset ID、split、审核和 manifest。
- 本轮的 `DB_FINAL_MESSAGE_METADATA_ONLY` 仅代表“具有可定位的已完成 Assistant 消息”，不能证明是单次 Provider Completion，不证明世界独立、使用权或可训练资格。

## Supabase 实际连接发现

已连接的 MCP 数据库用户是 `supabase_read_only_user`：`transaction_read_only=on`、`row_security=on`，**但 `rolbypassrls=true`**。因此本轮**没有对该连接运行任何生产业务行查询**。只从 `pg_catalog` 检查了候选表字段和索引，发现 `v2_chat_messages` 存在 `story_id` 前导索引；`user_stories` 存在作者与来源相关索引。这只是结构事实，不是可见候选数量。

已知当前 R60 受限数据库基线是本机 `r58_export_reader`，后者适用于先前的元数据 P0，但**不应假定已对消息表授予必要列的 SELECT 或具备合适的 Owner 限域 RLS**。未完成权限审查时工具会 HOLD。跨站点读取全部用户消息、使用 service_role 或切换 bypass 角色都不允许。

## 新增最小工具（合成测试，不含真实故事）

- `experiments/r58_quality/r60_dual_track_coverage.py`
- `experiments/r58_quality/test_r60_dual_track_coverage.py`

行为：

1. 只读取 Owner 本地 0600/0700 私有作品 ID 白名单。它是**本次预筛的明确范围**，不是作品权益与独立世界已经核证的声明。
2. 限制最多 16 个 Story；按 `story_id` 既有索引逐个查询，每条 SQL 3 秒 statement timeout、1 秒锁超时；每 Story 最多取 20 条最终 `assistant/completed` 消息候选。
3. 仅查询 `id/session_id/turn_index/created_at/status`；没有 SELECT 正文或 JSONB。ID 仅写 Owner 私有 0600 文件；SAFE 只报聚合。
4. `current_user` 必须 `r58_export_reader`、`rolbypassrls=false`、`rolsuper=false`、只读事务、`row_security=on`，并在业务查询前验证目标表 RLS 启用、`story_id` 列可读且索引存在。
5. 不创建任何 A/B 证据、Quality-v1 PASS、Owner 签核或训练数据。即使查到数百条也只算未经审核的 DB 元数据候选。
6. R50 禁止访问；不得使用 R50 Story/Session 作白名单或从 R50 资料中寻找范围。

**额外安全门槛**：在受限账号运行之前，Owner DBA 应先确认 `v2_chat_messages` 的现有 SELECT 列权限与 RLS 条件只允许访问本次合法范围；当前工具的角色检查本身不等于已经证明 RLS policy 具有租户级授权。若 Reader 对该业务表仍缺最小权限，请先决定是否使用经审核的专用聚合 RPC，而不是自动授予宽泛整表 SELECT。

## Owner Mac 执行（需由 Owner 准备真实白名单）

```bash
set -euo pipefail
set +x
umask 077
cd "$HOME/workspace/storyforge-r60-ledger-diagnostics"
git fetch origin r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter
export PYTHONPATH="$PWD/experiments/r58_quality:$PWD${PYTHONPATH:+:$PYTHONPATH}"

python3 -m pytest -q experiments/r58_quality/test_r60_dual_track_coverage.py

# 本次范围文件需要 Owner 从其拥有/授权的作品库存真实选出 1–16 个 ID；
# 禁止使用 R50/全站随机 Story。内容仅作为示意，不能照抄提交。
# {"schema":"storyforge_r60_owner_story_scope_private_v1",
#  "scope_note":"OWNER_APPROVED_CANDIDATE_DISCOVERY_ONLY",
#  "story_ids":["<真实的已授权作品 ID>"]}

SCOPE="$HOME/.local/share/storyforge/r59/private/<0700已有目录>/R60_OWNER_STORY_SCOPE_PRIVATE.json"
OUT="$HOME/.local/share/storyforge/r59/private/r60-dual-track-coverage-$(date -u +%Y%m%dT%H%M%SZ)"

test -n "${STORYFORGE_SUPABASE_DSN:-}"
python3 experiments/r58_quality/r60_dual_track_coverage.py \
  --owner-story-scope "$SCOPE" --output-dir "$OUT"
```

返回 `R60_DUAL_TRACK_COVERAGE_SAFE.json` 的聚合结果即可；不可发送私有候选 JSONL。若 `OWNER_SCOPED_COVERAGE_HOLD`，只报告 reason_code，不提升数据库权限自动重试。

## 下一次真正进入高价值筛选的条件

1. **合法范围**：Owner 为新候选提供已审核的作品/作者范围；E0 权益、隐私仍逐案证明，不能凭 public/owned flag 直接通过。
2. **真实规模**：先用本工具在受限 RolePlay Reader 上取得可信的 metadata-only 候选覆盖率；0 条要区分权限/RLS 与确实没有记录。
3. **世界组件**：对聚合候选的 Story ID 在 Owner 本地按来源世界图和角色关系作组件分组，不用 Story ID 冒充独立世界；保护集只用授权元数据核对。
4. **E2**：过滤 auto-continue、retry、fallback、后处理及不完整监督目标；缺 attempt/response 链则保留 HOLD，不能从 `status=completed` 假定单次 Provider 输出。
5. **两轨各自筛选/冻结**：严格线仅 A/B 可继续；实验线允许明确标注重建上下文但需合法单次监督标签语义。两轨可分别用 `quality_v1.py` 的评分标准、R59 的 SFT Shape / CPU Collator；不得共用冻结数据集 ID、Validation 集或统计准入。
6. **所有 Gate**：E0–E3 实证、E4 独立 Train/Validation 冻结、E5 真实 CPU Collator、E6 明确 GPU 和预算授权；此次不执行训练。

若现有受限账号不具备经审核的 Owner 限域 SELECT，则本阶段应输出 `OWNER_SCOPED_COVERAGE_HOLD`，由 Owner 审核增补只读接口，禁止改用当前绕过 RLS 的 Supabase Connector。

## 执行环境区分（Owner 确认）

- ChatGPT 直接调用 Supabase 连接器：`supabase_read_only_user`，只读、但拥有 BYPASSRLS，仅按已授权范围执行限定的聚合和诊断查询。
- Owner Mac 使用 `STORYFORGE_SUPABASE_DSN` 的本地 Python 脚本：`r58_export_reader`。`r60_dual_track_coverage.py` 和 `r60_scoped_target_pairs.py` 都要求此角色且不得 BYPASSRLS。
- 切勿把连接器的实际角色套用到本地执行说明；本机遇到 `DATABASE_GUARD_HOLD` 或表 SELECT/RLS 权限不足时，应核证原权限与来源，不应切换到旁路账号。
