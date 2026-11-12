# StoryForge R50：Owner Mac 冻结文件定位与权限HOLD恢复（2026-11-12）

> 本文件保存**已由Owner实际只读查找到的本机路径**，不是可由ChatGPT连接器直接访问的路径。只记录文件位置/角色，不写入私有文件内容、来源ID、原始SHA或JSON值。所有路径在Owner机器上才有效，未来机器迁移需复核。未发现原始50条文件的当前绝对路径，未识别最终冻结排除集。R50全量隔离HOLD、训练准入0。

根目录：`$HOME/.local/share/storyforge/r50`。

## 已找到的关键文件（确切相对路径）

| 角色 | 根目录下路径 | 证据状态 |
|---|---|---|
| 46条PRESEAL候选 | `run.dWgMu5/private/derived/R50_CANDIDATE_46_PRESEAL_PRIVATE.jsonl` | 46行可解析，非最终封存证明 |
| 对应46条来源provenance | `run.dWgMu5/private/derived/R50_PROVENANCE_46_PRESEAL_PRIVATE.jsonl` | 46行可解析，未验证逐案一致 |
| 46选取清单 | `run.dWgMu5/private/derived/R50_46_PRESEAL_SELECTION_MANIFEST_PRIVATE.json` | 已读出字段名，值/冻结状态待核 |
| 46准入状态 | `run.dWgMu5/private/R50_46_ADMISSION_STATUS_20261016.json` | 已读出字段名，值待核 |
| 46→R45精确子集屏查 | `run.dWgMu5/private/derived/R50_46_R45_ORIGINAL_EXACT_SUBSET_SCREEN.json` | JSON根对象21个键，不是21条排除 |
| 原始世界清点 | `full-original-worlds/run.cGUPnjdx/R50_FULL_ORIGINAL_WORLD_INVENTORY_PRIVATE.json` | 结构已见，不能当最终封存 |
| R45全来源门禁 | `r45-full-source-gate/R50_R45_FULL_SOURCE_GATE_20261022_220215.json` | 结构已见，不能直接代表R50隔离 |
| 46 PRESEAL阶段审计 | `run.dWgMu5/private/derived/R50_46_STATIC_INPUT_PREFLIGHT_PRIVATE.json` | 已找到，未核内容 |
| R45精确源门禁报告 | `run.dWgMu5/reports/R50_R45_FULL_GATE.json` | 已找到 |
| 其他HF CPU46阶段输入 | `hf-cpu46/r50-cpu46-20261022T164410Z-305591/stage/private/R50_CANDIDATE_46_PRESEAL_PRIVATE.jsonl` | 是历史Stage，不能替代冻结原件 |
| HF CPU46技术结果 | `hf-cpu46/r50-cpu46-20261022T164410Z-305591/results/R50_CPU46_TOKEN_REPORT_SAFE_AGGREGATE.json` | 先前CPU技术记录，非R50封存 |
| 其他排除文件 | `../r58/private/quality-v1/QUALITY_V1_EXCLUSION_SAFE.json` | R58质量排除，不可冒充R50保护集 |

## 本次真实失败和处理原则

Owner在执行 `scripts/r60_r50_preseal_crosswalk_cpu.py` 得到 `R50_PRESEAL_CROSSWALK_HOLD` / `FILE_PERMISSION_HOLD`，`preseal_cases_checked=0`、`case_id_order_exact=false`、`train_admitted=0`。这表示**文件读取权限门禁先阻断**，并不表示46条已产生case ID错配。原因是crosswalk严格要求所有6个输入都符合`mode & 0o077 == 0`，即对group/other无读写执行位；原始R50的某个文件mode更宽松。当前**不知道哪一个文件**，也不知道具体mode。不得直接对历史冻结原件递归chmod，更不能为了测试覆盖改变原始mtime/哈希/内容。

安全恢复策略：使用Owner本机`mktemp -d`创建0700私有临时目录，**只读原件复制到新的文件**、原文件保持不变；对副本chmod600，并在Owner本地比较每份原件与副本SHA256；使用副本运行同一跨文件校验器，最后删除**仅这次临时副本**。命令与完整6路径见下方。**如果原件 symlink 或非普通文件，或两边SHA不匹配，则立即HOLD，不绕过。**

```bash
set -euo pipefail
umask 077
cd "$HOME/workspace/storyforge-r60-4router-review"
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
B="$HOME/.local/share/storyforge/r50"
D="$B/run.dWgMu5/private/derived"
ORIG=(
  "$D/R50_CANDIDATE_46_PRESEAL_PRIVATE.jsonl"
  "$D/R50_PROVENANCE_46_PRESEAL_PRIVATE.jsonl"
  "$D/R50_46_PRESEAL_SELECTION_MANIFEST_PRIVATE.json"
  "$B/run.dWgMu5/private/R50_46_ADMISSION_STATUS_20261016.json"
  "$B/full-original-worlds/run.cGUPnjdx/R50_FULL_ORIGINAL_WORLD_INVENTORY_PRIVATE.json"
  "$B/r45-full-source-gate/R50_R45_FULL_SOURCE_GATE_20261022_220215.json"
)
TMP="$(mktemp -d "$HOME/.local/share/storyforge/r60/private/r50-crosswalk-copy-XXXXXXXX")"
chmod 700 "$TMP"
# 只复制文件，不修改原件
for i in 0 1 2 3 4 5; do
  src="${ORIG[$i]}"
  test -f "$src" && test ! -L "$src"
  dst="$TMP/f$i"
  cp "$src" "$dst"
  chmod 600 "$dst"
  SRC_SHA="$(shasum -a 256 "$src" | awk '{print $1}')"
  DST_SHA="$(shasum -a 256 "$dst" | awk '{print $1}')"
  test "$SRC_SHA" = "$DST_SHA"
  # 只输出固定位置编号和无私有值状态
  echo "R50_COPY_$i=SHA256_MATCH"
done
"$PY" scripts/r60_r50_preseal_crosswalk_cpu.py \
  --cases "$TMP/f0" --provenance "$TMP/f1" \
  --selection "$TMP/f2" --admission "$TMP/f3" \
  --worlds "$TMP/f4" --r45-gate "$TMP/f5"
# 检查完再手动删除本次新建的副本目录；不要删除r50原件。
```

上述样例故意**没有自动删除临时目录**，使HOLD时可以保留核查证据；确认结果后由Owner只对新建的TMP执行`rm -rf -- "$TMP"`。如果交互shell退出丢失TMP变量，可按此前输出或只读查询确切新目录，不做宽范围删除。任何新的SAFE回执只输出状态和布尔值，不输出原始SHA。

## 后续证据门禁

- `R50_PRESEAL_46_CROSSWALK_PASS__FINAL_COVERAGE_HOLD` 最多证明46条PRESEAL `case_id`逐行匹配与报告关键字段存在。
- `FILE_PERMISSION_HOLD` 不是来源不一致；`case_id_order_exact=false`在`preseal_cases_checked=0`时只是初始默认值。
- 最终隔离还要核对原始50→剔除4→46、最终seal与R45全来源别名/世界隔离、Common2两个训练候选的故事/会话/消息交集。以上全部尚未完成，不自动启动GPU/SFT。

## 2026-11-12 ChatGPT资料库恢复位置（最新）

**已找到、已校验但尚未转存到Mac本地的原始50条文件**：ChatGPT资料库根目录 `/StoryForge_R50_PRIVATE_NewChat_Handoff_20261016.zip`、`/R50_FRESH_HELDOUT_50.jsonl`、`/R50_CASE_PROVENANCE_50.jsonl`。历史私有ZIP 368932字节、16条目ZIP校验通过；两个JSONL分别422562/31758字节，SHA256与2026-10-16冻结交接记录和ZIP内原件严格一致。SHA和具体证据见 `R60_COMMON2_TRAIN_ADMISSION_GATES_20261112_CN.md`。这些资料库路径不是Mac绝对路径，**不能把ChatGPT资料库读取成功当作文件已经存在Mac本地**。在Owner手动下载并核对后，才补充Mac最终安全存放位置；保持0600/0700、禁止公开Git提交原件或更改既有PRESEAL副本。以前“原始50份找不到”状态被此条更新取代，但最终R50封存和完整排除仍HOLD。

## 2026-11-12 Owner Mac原始50条落盘完成（替代此前“尚未转存Mac”描述）

已得到Owner真实Mac `shasum -a 256` 收据：以下两份文件现已存在 `/Users/keedle/.local/share/storyforge/r50/original-frozen-20261016/`，并与2026-10-16历史原始冻结字节SHA256精确一致：

- `R50_FRESH_HELDOUT_50.jsonl` SHA256 `8dbb66aeb47fd1fec34718d31b228c0378a79f43b7b847eb3e403752d8139781`
- `R50_CASE_PROVENANCE_50.jsonl` SHA256 `9306af53c6a53fbe46a6675c50e5fac4753162a5c19d6f3c1a0072919306b280`

该目录为原始50案冻结资料的Mac长期只读引用位置，禁止程序覆盖或将文件提交公开Git。ZIP是否同时落盘至该目录当前未经Owner收据确认，**不要把JSONL恢复PASS解释为ZIP也已在Mac**。下步使用新脚本 `scripts/r60_r50_original50_complement_cpu.py` 与已存在PRESEAL46及排除4的SHA副本只读核验完整50=46+4补集；完整R50 seal、R45世界级隔离和Common2与R50故事/会话/消息交集仍HOLD，训练准入0。
