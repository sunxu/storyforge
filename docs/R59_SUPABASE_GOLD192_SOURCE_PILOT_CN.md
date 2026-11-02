# R59 Gold192 → Supabase Source Pilot（Owner 私有执行）

## 目的与边界

本步骤只生成 **Gold192 来源证据**，不生成正式可训练的 Quality-v1，也不授权 GPU。
复用现有 Reviewer A/B、11 条训练排除记录和 Gold192 冻结 source packets。
数据库查询仅涉及 packets 所列的 13 个故事及目标 turn，不扫描 Supabase 全库。
私有正文、角色卡、消息主键只进入 Owner 私有目录，不进入 GitHub 或 CI 日志。

代码：`experiments/r58_quality/r59_gold192_supabase_extract.py`。
当前固定输入 SHA256：

| 文件 | SHA256 |
| --- | --- |
| A Results | `641b71e10a14318b57e69cb0239172f7016fe5b9d2149923f876308f5e6fe1e4` |
| B Results | `bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8` |
| 11 Excluded | `9ca99432e08b680cb67b5a1f89d172a337cb91c9bd02af70b68356938c6c04ed` |
| Gold192 source packets | `ae26a288382939aa79923d4a4c0602b0d575baa63f81c622ab362fbb70d56a5e` |

## Mac 执行（不需要 GPU）

先在现有 `gold-quality/unified-pipeline-v1` 工作树检查 `git status --short`，
只有确认可以 fast-forward 时才 `git pull --ff-only`；禁止 reset、force push 或覆盖未提交工作。

设置本机路径（根据已存在的私有文件位置修改）：

```bash
set -eu
REPO="$HOME/workspace/storyforge-gold-quality"
PRIVATE="$HOME/.local/share/storyforge/r58/private"
R59_PRIVATE="$HOME/.local/share/storyforge/r59/private"
mkdir -p "$R59_PRIVATE"
chmod 700 "$R59_PRIVATE"
A="$PRIVATE/R58_GOLD192_REVIEWER_A_RESULTS_20261102.json"
B="$PRIVATE/R58_GOLD192_REVIEWER_B_RESULTS_20261102.json"
EX="$PRIVATE/quality-v1/QUALITY_V1_EXCLUDED_CASES.jsonl"
PACKETS="$R59_PRIVATE/GOLD192_STORY_REVIEW_PACKETS_PRIVATE.jsonl"
```

若 `PACKETS` 尚不存在，只从原交接 ZIP 解出该 JSONL 到私有目录：

```bash
ZIP="$HOME/Downloads/StoryForge_Gold_Quality_Handoff_20261102_v2(1).zip"
test ! -e "$PACKETS"
(umask 077; unzip -p "$ZIP" \
  'StoryForge_Gold_Quality_Handoff_20261102_v2/private/source_packets/GOLD192_STORY_REVIEW_PACKETS_PRIVATE.jsonl' \
  > "$PACKETS")
test "$(shasum -a 256 "$PACKETS" | awk '{print $1}')" = \
  ae26a288382939aa79923d4a4c0602b0d575baa63f81c622ab362fbb70d56a5e
```

只读身份门禁（不连接数据库，不写训练内容）：

```bash
python3 "$REPO/experiments/r58_quality/r59_gold192_supabase_extract.py" \
  --reviewer-a "$A" --reviewer-b "$B" --exclusions "$EX" \
  --source-packets "$PACKETS" --output-dir "$R59_PRIVATE/not-created" \
  --identity-only
```

预期：`gold192=192`、`excluded_disagreements=11`、`priority_candidates=72`。

## 数据库只读连接与试运行

在 Owner Mac 的 Python 环境安装可选连接器：

```bash
python3 -m pip install 'psycopg[binary]'
```

从本机私有凭据管理器取得 **只读 PostgreSQL DSN**，设为
`STORYFORGE_SUPABASE_DSN` 环境变量。不要将连接串、凭据或 token 复制到聊天、
仓库、命令历史或 CI；脚本强制 `SET TRANSACTION READ ONLY`。

首次试运行（7 条；输出目录必须尚不存在）：

```bash
python3 "$REPO/experiments/r58_quality/r59_gold192_supabase_extract.py" \
  --reviewer-a "$A" --reviewer-b "$B" --exclusions "$EX" \
  --source-packets "$PACKETS" \
  --output-dir "$R59_PRIVATE/r59-source-pilot7" --pilot 7
```

检查 SAFE 而非私有正文：

```bash
python3 -m json.tool "$R59_PRIVATE/r59-source-pilot7/R59_SOURCE_SAFE.json"
```

期望 192 个来源 locator、13 个故事快照、7 个请求上下文；实际导出
数量与失败分类由 SAFE 报告决定，不能假定全部成功。

试运行验证后，执行全部 72 条优先候选（**新建**目录）：

```bash
python3 "$REPO/experiments/r58_quality/r59_gold192_supabase_extract.py" \
  --reviewer-a "$A" --reviewer-b "$B" --exclusions "$EX" \
  --source-packets "$PACKETS" \
  --output-dir "$R59_PRIVATE/r59-source-priority72" --pilot 0
```

输出：

- `R59_SOURCE_LOCATORS_192.jsonl`：192 个目标的精确来源与匹配状态；
- `R59_SOURCE_CONTEXT_PRIVATE.jsonl`：符合源匹配和历史结构门禁的原始前序历史；
- `R59_STORY_DRAFTS_PRIVATE.jsonl`：13 个当前数据库故事配置快照；
- `R59_SOURCE_SAFE.json`：数量、哈希、状态的 SAFE 回执。

所有输出通过 `O_EXCL` 创建（无覆盖），文件权限为 0600。
对多会话同文案的目标，必须能唯一定位根会话，否则 `IDENTITY_AMBIGUOUS`；
任何历史超过 `--max-history` 的案例不得被静默截断。

## 后续门禁

`CURRENT_V2_DATA_NOT_HISTORICAL` 只代表当前故事配置：**不是**
历史生产 System Prompt 的精确回放。训练用 Prompt 必须独立调用
`sunxu/RolePlay` 的 `buildV2RuntimePromptParts` 构建，并记录代码 commit
与 `baseMode`（legacy/native）。未经独立检查的会话摘要不进入训练输入。

之后复用既有 Quality Pipeline、历史训练曝光核验和 HF CPU Tokenizer
`src/storyforge_dataset/token_preflight.py`；再进行 `last_round`
collator 验证。至此方可冻结 Quality-v1，进入 GPU smoke 和正式 SFT。
