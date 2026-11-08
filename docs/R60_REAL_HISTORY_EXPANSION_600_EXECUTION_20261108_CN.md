# R60-REAL P0：真实历史 SFT 扩样 6 → 600 执行书（2026-11-08）

状态：**扩样代码、合成测试与生产 SQL 计划校验已完成；Owner Mac 尚未运行真实扩样。GPU 不启动。**

## 1. 已有生产事实与优先级

Owner Mac 返回可信 SAFE：现有 G1 `R60_REAL_G1_CAPTURE_PRIVATE.jsonl` 已成功采集 **6 条、6 个 Story**，并已生成 6 份未填写 Reviewer 模板，目录 0700、文件 0600，生产 DB 未修改。**原 6 条必须保留，不得重新抽样或重置 case_key**。

本轮只读生产 G0 新核验：从作者本人游玩、已发布、未删除、原创/私有、根 Session（没有 `parent_session_id` / `forked_from_turn`）、有效 30+ 轮的作品中，稳定抽取 96 个 Story，检查每个 Story 最近 12 条 completed Assistant：**1,152** 条目标里，**339** 条满足「目标前连续 User→Assistant→User、长度 300–1500、正常 finish、无可见编辑或解析异常」等技术条件，覆盖 **67 个 Story**。统计来源为生产只读聚合，不含任何私人正文或身份标识；样本不代表模型质量 PASS，也不代表全库通过率。新扩样 SQL 已在生产库 `EXPLAIN` 通过语法/规划检查，但**未在连接器中运行正文导出**。

正式优先级调整：
1. **P0：扩真实历史候选**，第一轮总目标 600 条（包含原 6 条）；根据实际可用量与 SAFE 质量结果在 500–1000 之间调整下阶段目标。
2. **P0：批量 AI 质量筛选与严重缺陷排除**，先用现有 6 条校准标准，不阻塞扩样。
3. **P0：真实目标前输入完整性、世界关联与 R50 完整元数据隔离**（只使用 R50 身份/世界元数据，不读取正文）。
4. **P1：冻结独立训练/验证世界、Qwen Tokenizer 与 ms-swift Collator CPU 预检**。
5. **P1：首批正式 GPU LoRA SFT 单独预算审批**。不重复早期 GPU smoke。

### 为什么不是改 `MAX_CASES=6`

现有 `r60_real_private_batch.py` 是 6 条 G1 Pilot 的确证/双审工具。直接把 6 改为 1000 将造成单次大查询、无游标续跑、历史 ID 重复、崩溃恢复与私有文件过大。**新扩样独立程序**：
`experiments/r58_quality/r60_real_expand_private.py`。

## 2. 私有扩样器行为与边界

- `init`：只读取**已采集的原 6 条**作为 seed，校验 JSONL、历史/目标 SHA256、6 个 Assistant 消息 ID 的唯一性；创建新 0700 扩样目录与 0600 版本化私有配置。**原 Pilot 文件不修改、不复制到 GitHub**。
- `advance`：使用 `r58_export_reader` DSN，验证 `READ ONLY + row_security=on + BYPASSRLS=false + superuser=false`；每页严格 `REPEATABLE READ READ ONLY`、30 秒语句超时，Story 稳定 `(md5(story_id),story_id)` 游标，默认 **20 Story/页 × 最近 20 个完成回复 × 最多 4 个合格案例/Story**，每页上限 80 条，单次调用最多 5 页。单个 DB 事务不跨页，减轻对生产查询的压力。
- `R60_EXPAND_PAGE_NNNN_PRIVATE.json`：每页内容含精确 story/session/message IDs、目标前真实历史、目标正文、source hashes、游标、故事行与完整性校验；新文件 `0600`，先写临时文件再原子替换成**新**页文件，永不覆盖已提交页。
- `inspect`：**纯本地**，不需要 DSN，验证 seed 原始 SHA、配置 SQL 版本、逐页 SHA、页序、游标单调、跨页目标 Assistant ID 不重复、历史和 target SHA 与案例来源状态；仅打印 SAFE 计数。
- `advance` 每次开始也重新加载所有已完成页、验证上述不变量，继续下一页；多进程用 `flock` 互斥。单页查询失败不会删除已完成页；当前批没有任何来源可验证时默认 HOLD，绝不凭空 PASS。
- 首批只选明显根 Session，减少 fork 历史缺漏；并**不**由此推出跨作品世界依赖已排除。仍使用 `DB_FINAL_PERSISTED_ASSISTANT` 监督目标，不伪称原始 Provider 单次 completion 或历史实际 System。
- 不处理 R50 正文，不改 RolePlay、Gold192 或生产 DB，不对候选做训练准入，不运行 HF/GPU。
- `SAFE` 只有累计样本数、已扫 Story、页数、状态码和硬门槛；**不打印**私有 ID、case key、目标 SHA、正文或凭据。真实数据只存 Owner Mac；不能把私有页传到 Public GitHub。

## 3. Owner Mac 执行：复用之前成功的 6 条（不再执行 G1 capture）

在 StoryForge 仓库根目录、最新 R60 分支下运行。用户原先成功的 G1 目录可能带时间戳，须将 `PILOT` 指向**已含 29562-byte 原始捕获文件**的那一个目录。新的 `EXPAND` 路径需不存在。

```bash
set -euo pipefail
set +x
umask 077
git fetch origin r60/gold192-history-v3-adapter
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter

BASE="$HOME/.local/share/storyforge/r60/private"
# 替换为前次实际成功目录：不重新运行旧 capture
PILOT="$BASE/g1-pilot-实际时间戳"
SEED="$PILOT/R60_REAL_G1_CAPTURE_PRIVATE.jsonl"
EXPAND="$BASE/r60-expand-first-600"
test -f "$SEED"
test ! -e "$EXPAND"

python3 experiments/r58_quality/r60_real_expand_private.py init \
  --output-dir "$EXPAND" --seed-capture "$SEED" \
  --page-size 20 --target-total 600
```

随后在 **同一 shell 安全设置** `STORYFORGE_SUPABASE_DSN` 指向 `r58_export_reader`（可复用此前成功的加载方法；**不要贴在聊天或 GitHub**），再启动一轮最多 5 页：
 
```bash
test -n "${STORYFORGE_SUPABASE_DSN:-}"
python3 experiments/r58_quality/r60_real_expand_private.py advance \
  --output-dir "$EXPAND" --max-pages 5
```

根据 SAFE `total_candidates`，重复上一条 `advance` 指令直到 `EXPANSION_TARGET_REACHED__NOT_ADMITTED` 或 `EXPANSION_EXHAUSTED__NOT_ADMITTED`。所有已提交页自动跳过且不会重复计入。页面上限 5 是一次命令的防护额度，不影响多次增量执行。

无需 DSN 的检查：

```bash
python3 experiments/r58_quality/r60_real_expand_private.py inspect \
  --output-dir "$EXPAND"
```

最终只需要发给 ChatGPT **`init`/ `advance` / `inspect` 的 SAFE JSON**。禁止上传 `R60_EXPAND_CONFIG_PRIVATE.json`、`R60_EXPAND_PAGE_*_PRIVATE.json`、`R60_REAL_G1_CAPTURE_PRIVATE.jsonl`；这些文件包含真实来源、私有对话和/或 SHA。

## 4. 后续工作验收

| 里程碑 | 验收 |
|---|---|
| EXPAND-01 | 原 6 条 Seed 完整 SHA PASS；配置创建、真实 G0 96 Story/339 条聚合已实测 |
| EXPAND-02 | 扩样器 13 项合成测试/CI；生产实际首 5 页 SAFE，页次和去重 PASS |
| EXPAND-03 | 新累计候选总数达到 500–1000 或记录全量数据枯竭（EXHAUSTED）；有跨 Story 分布 |
| QUALITY | 批量独立 AI 审核、严重问题排除，按六维标准选入质量池；拒绝低质/越权/不安全回复 |
| ISOLATION | 完整 R50 元数据和世界组件依赖验证、目标前信息与规范化 System 一致性 |
| CPU | 冻结 Train/Validation，Qwen Tokenizer + ms-swift Collator 真实 CPU PASS |
| GPU | **仅在数据集已准入且 Owner 单独批准预算后**，启动正式 GPU SFT |

**截至本执行书写入：扩样程序代码已提交；生产真实扩样仍为 0 个新增案例、原 Seed=6；不能把 339 G0 技术候选冒充已落盘的训练候选。**
