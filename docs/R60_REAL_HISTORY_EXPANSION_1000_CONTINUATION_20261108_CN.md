# R60-REAL：真实历史候选池 600 → 1000 原位扩容执行书（2026-11-08）

## 已完成的真实数据里程碑

Owner Mac 返回的最新实际 SAFE（扩样器 `inspect`）：

- `status=EXPANSION_TARGET_REACHED__NOT_ADMITTED`
- `seed_cases=6`，`new_cases=594`，`total_candidates=600`
- `private_pages=12`，`stories_scanned=240`
- `quality_pass=0`，`train_admitted=0`
- `r50_complete_exclusion_verified=false`、`world_isolation_verified=false`
- `database_modified=false`、`gpu_started=false`、`r50_body_accessed=false`

**Owner 最新授权调整：真实历史候选池继续扩充到 1000。** 这仅调整候选扩样上限，绝不自动进行质量准入或付费 GPU 训练。

## 变更方式：在原目录增加不可覆盖的扩容回执

新增 `experiments/r58_quality/r60_real_expand_private.py extend --target-total 1000`，在原 600 目标不变的情况下新增独立文件：

`R60_EXPAND_TARGET_EXTENSION_PRIVATE.json`

- 仅支持 **已完成并已校验的 600 → 1000**；若不满足 `total_candidates=600`、源配置目标 600、未耗尽 Story，则返回 SAFE HOLD。
- 对原私有 `R60_EXPAND_CONFIG_PRIVATE.json`、Seed 和已有的 12 页**均不修改**；扩容回执绑定原配置的 SHA、截止 600 条的页数、累计数、最后一页完整文件哈希与游标，并有自身字段校验。
- 同一扩容命令重复运行会验证现有扩容回执后安全返回相同结果，不覆盖它；任何扩容回执篡改、旧页内容变动、旧页截断、断裂或越界均 HOLD。
- `inspect` 和 `advance` 会严格验证有效扩容回执并把新的候选上限视为 1000；仍然坚持分页查询、Assistant ID 跨页精确去重、完整 SHA、`r58_export_reader` + READ ONLY/RLS。
- 扩容本身是**仅访问 Owner Mac 私有文件**的操作，不使用 DSN、不联网、不读 R50 正文、不更改数据库、不启动 GPU。
- 源数据目标仍是 `DB_FINAL_PERSISTED_ASSISTANT`，未知历史 System 不得伪称实际发送；没有通过世界组件、完整 R50 排除和质量审核之前 `train_admitted=0`。

## Owner Mac：直接复用既有 `r60-expand-first-600`，绝不重新 `init`

在 StoryForge 仓库根目录：

```bash
set -euo pipefail
set +x
umask 077
git fetch origin r60/gold192-history-v3-adapter
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter

BASE="$HOME/.local/share/storyforge/r60/private"
EXPAND="$BASE/r60-expand-first-600"
test -f "$EXPAND/R60_EXPAND_CONFIG_PRIVATE.json"

# 先检验现有 600 条/12 页，完全不需要 DSN
python3 experiments/r58_quality/r60_real_expand_private.py inspect \
  --output-dir "$EXPAND"

# 原位扩容：创建新的 0600 授权回执，绝不改动既有页面
python3 experiments/r58_quality/r60_real_expand_private.py extend \
  --output-dir "$EXPAND" --target-total 1000

python3 experiments/r58_quality/r60_real_expand_private.py inspect \
  --output-dir "$EXPAND"
```

期待扩容 SAFE：`status=EXPANSION_TARGET_EXTENDED__NOT_ADMITTED`、`total_candidates=600`、`target_total=1000`。随后 inspect 应显示 `EXPANSION_IN_PROGRESS__NOT_ADMITTED`。

在**相同已有 Owner Mac 终端**安全注入 `STORYFORGE_SUPABASE_DSN`（须为 `r58_export_reader`），执行多轮受控分页。这里不建议读取或打印 DSN：

```bash
test -n "${STORYFORGE_SUPABASE_DSN:-}"

for i in 1 2 3 4 5 6; do
  SAFE="$(python3 experiments/r58_quality/r60_real_expand_private.py advance \
    --output-dir "$EXPAND" --max-pages 5)"
  printf '%s\n' "$SAFE"
  STATUS="$(printf '%s\n' "$SAFE" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
  case "$STATUS" in
    EXPANSION_TARGET_REACHED__NOT_ADMITTED|EXPANSION_EXHAUSTED__NOT_ADMITTED)
      break ;;
  esac
done

python3 experiments/r58_quality/r60_real_expand_private.py inspect \
  --output-dir "$EXPAND"
```

上面的扩容后续跑最多增加 30 个分页查询（最多 600 Story），每次调用最多 5 页；遇到进程异常或数据库超时 `set -e` 自动终止，已完成页会保留。达到 1000 或自然候选耗尽时自动停止，不会扩到 1001。不要删除已有文件、重新 `init`，也不要把私有 JSON/正文/DSN 上传 GitHub。

## 执行与验收

- 首轮精确 600 条数据已采集，扩容新程序与**26 项合成测试**已提交；CI 通过不代表 Owner Mac 已经执行实际 `extend` / `advance`。
- 最终 `inspect` 若 `total_candidates=1000` 且 `status=EXPANSION_TARGET_REACHED__NOT_ADMITTED`：技术候选阶段达标，进入批量质量 AI 审核；否则按 SAFE 原因码处理，不伪造完成。
- 质量合格目标参考 200–400，但不保证通过率；未经真实双审和保护集/世界核验不能计入训练集。
- 训练准入仍为 0，GPU 训练仍需单独批准。

**用户只需回传 `extend`、最终 `inspect` 的 SAFE JSON；所有文本与 ID 留在 Owner Mac。**
