# StoryForge R58 — Owner UUID 世界身份规则生效后的 G1 下一步（2026-10-30）

## 本次新事实（Owner 直接声明）

Owner 明确确认：**RolePlay 与 R57 使用同一故事 UUID 命名空间；已知故事均来自 RolePlay；一个 story UUID 就是一个独立语义世界**。本轮 R58 采用此声明作为身份约定。无需重复进行跨故事别名、标题或世界设定相似性的语义判定，不将 R57 之前尚未完成的 55 对别名审查强加到本轮。**这条规则仅对 R58 RolePlay 作品身份适用，不追溯改写历史研究原始审核结论。**

记录：`docs/evidence/R58_OWNER_ROLEPLAY_UUID_WORLD_IDENTITY_POLICY_SAFE_20261030.json`。新代码以规范化的 `story_id.lower()` 作为 `world_component`；旧版 `owner_world_graph_reviewed` 和 `world_component` 私有 CSV 列继续存在以兼容旧格式，但不会被要求另行填写。**后续需有 R50、历史 SFT、R55/R57 Dev 和其他保护 UUID 集合的可信排除证据。**

## 本次 5 条冻结候选的结论

Owner Mac **69/69** 合成测试 PASS，R57 29 条故事 UUID 私有元数据名录格式通过（历史 SFT 27 条），与当前五个故事 UUID 精确交集 **1**：

- 命中 1：`EXCLUDED_PRIOR_SFT_EXACT_UUID_EXPOSURE`。这条从后续独立训练候选准入中排除；**不重新替换，不增补第六条故事**。
- 未命中 4：对 **R57 已核对的 27 个历史训练 UUID 集合**无同 UUID 重叠；按 Owner 世界身份规则，不再做“别名不同但同一语义世界”的额外证明。**但其他时期训练来源是否已被完整列入 R57 27 集、以及 R50/Dev/其他保护世界 UUID 集仍需依据冻结索引核实**。
- 五个故事 G1 仍未完全通过；四个也尚不能读取回复正文或训练。

## 统一 Mac 本地安全核对（不改写五条队列）

更新到最新 R58 Draft 分支，运行纯合成测试。旧 69 项 + 原先新增的隔离账本 4 项 + 本轮身份规则 2 项及选择器 2 项，预期 **80 项**；Owner Mac 尚未验收。

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only

python3 -m unittest discover \
  -s experiments/r58_round1 \
  -p 'test_*.py' -v &&

ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
python3 experiments/r58_round1/check_prior_sft_exact_world_ids.py \
  --private-queue "$ROOT/g1_review_queue_private.csv" \
  --private-discovery "$ROOT/g1_index_candidates_autodiscovered_private.json" \
  --private-hold-output "$ROOT/g1_prior_sft_uuid_owner_policy_v2_private.json"
```

新版 shortlist 选择器要求提供 `--prior-sft-holds <本地 v2 账本>`；缺少账本即拒绝候选选择，账本标记历史 SFT 曝光的 UUID 即使其他保护标记误为 true 也被硬性排除。

新私有账本包含五条 story UUID、逐条曝露标记、规范化世界 UUID、来源 SHA；因此只能保留在 Mac 受控 0600 私有目录。**不要上传这个文件、哈希、真实 UUID 或 R50 内容**。脚本输出仍仅 SAFE 汇总；同一路径已存在时禁止覆盖。

新版输出 `candidate_id_namespace=OWNER_CONFIRMED_ROLEPLAY_STORY_UUID`，`owner_attested_one_uuid_one_world=true`，`r57_roster_only_exact_id_nonoverlap_count=4`，`exact_identifier_overlap_count=1`。仍保留 `g1_clearance=HOLD`、`r50_protection_checked=false`、`other_protected_worlds_checked=false`。

## 余下实际 G1 门禁（不再做语义别名重复劳动）

1. **R50 Protected**：仅使用已经授权的 R50 保护故事 UUID 元数据索引，覆盖所有保护世界，按照 story UUID 与四个候选做集合交集。**不打开 R50 测试题正文或答案**。
2. **R55/R57 Dev**：同样使用实际开发题与独立评估使用的故事 UUID 完整冻结索引；不需要检查人物、标题或语义别名。
3. **Other Protected**：核查其他独立留出集（含旧 Test/Holdout）、被保留世界的完整 UUID 注册表，避免把原本的保护世界纳入训练。
4. **Prior SFT source coverage**：已验证 27 个 UUID 的范围为 R57 已冻结的 v0.1、R46、R54 Train/Validation 来源；确认没有被遗漏的其他已执行训练集来源后，才能对四条没有命中的候选给 `prior_sft_clear=true`。

这些都是**UUID 级完整性与交集检查**，不需要再证明跨故事世界独立性。任何保护集索引缺失、不完整、未知则对应门禁 HOLD。

## 不改变的 R58 约束

最多 5 个世界、20 条目标候选回复；已命中的 1 条不补选，当前最多只能对余下 4 条开展必要的 G1 保护集核查。所有候选回复正文继续不读；G2 Runtime Replay、G3 双 Reviewer、G4 分区、G5 数据冻结均未开始；Train/Val/Teacher 0。PR #7 Draft、不合并、Skill v0.1 不改、HF CPU/GPU 不启动。首轮完成后、扩样前提醒仍有效，直到真正出现 `R58_ROUND1_PILOT_COMPLETION_SAFE.json` 的严格完成标记。

## 新增 fail-closed：正式 shortlist 的历史 UUID 硬排除

`pilot_round1_shortlist.py` 在携带 `--guards` 时，**现在也必须携带** `--prior-sft-holds`，引用同一批五个故事的 v2 私有曝光账本；缺失、格式不符、未覆盖 guard story ID 均 HOLD。即使手工误填某故事的 `prior_sft_clear=true`，已经命中历史 SFT UUID 的那个故事仍不得进入后续 shortlist。

**不要现在运行正式带 guards 的 shortlist**：R50、R55/R57 Dev、其他 protected UUID 及历史 SFT 来源完整性尚未通过；这四种保护布尔值目前保持 false。当前唯一应该运行的是上述本地私有账本核验命令，回传 SAFE JSON。生产数据无改写。
