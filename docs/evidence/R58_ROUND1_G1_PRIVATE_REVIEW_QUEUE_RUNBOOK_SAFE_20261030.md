# R58 Round1 G1 — 5 条私有元数据核验队列（SAFE）

**2026-10-30**。Owner 已从首次导出的 1284 条故事级元数据中，按既有条件筛选 **1280 条**：original 1106、dice_cocreate 91、ai_assisted 83。Owner Mac **23/23 合成测试 PASS**，CSV 布尔和条件瀑布检查通过。没有读取用户或角色对话正文。

## G1 下一步的实际对象：最多 5 个故事级记录，不是 5 个已独立世界

`experiments/r58_round1/prepare_round1_g1_review_queue.py` 按本轮预定的 **3 original / 1 dice_cocreate / 1 ai_assisted** 配额，从 1280 条元数据通过行中按会话数量、已完成回复数量、故事 ID 固定排序，形成**仅供 Owner 私有审查**的至多 5 条元数据队列。

**警告**：这些仅是候选 story_id。多个故事可能属于同一语义世界，也可能与 R50 保护集、既有 SFT 曝光世界或 R55/R57 Dev 世界冲突。没有这些证明时不得读取会话/回复正文，也不能自动补选其他故事。原冻结 Priority3 三案例不重选。

每个私有队列条目的全部 5 项门禁默认 `false`，`world_component` 和 `evidence_reference` 为空，`review_state=G1_HOLD`；源文件不存在则失败，输出存在则不覆盖。纯合成测试 7 项，Owner 实测待报告。不会联网或访问数据库，不读取 protected 集或任何文本。

### Mac 本地执行（只读现有私有 CSV）

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only

python3 -m unittest discover -s experiments/r58_round1 \
  -p 'test_*.py' -v &&

python3 experiments/r58_round1/prepare_round1_g1_review_queue.py \
  --inventory "$HOME/.storyforge-r58-private/round1_pilot_20261030/stories_private.csv" \
  --private-output "$HOME/.storyforge-r58-private/round1_pilot_20261030/g1_review_queue_private.csv"
```

预期共 30 项合成测试，`OK`。**只把 Python 命令打印出的 SAFE JSON 发到聊天**；不要发送 `g1_review_queue_private.csv`、story_id、用户身份或实际对话正文。若私有输出已存在，工具拒绝覆盖；先核对已有文件版本，不直接重跑覆盖。

### 如何审核五条 G1 项目

对这最多 5 个故事标识，在 Owner **本地**用受许可且无正文的来源/世界映射证据分别检查：

1. `owner_world_graph_reviewed`：从作品关系、世界标签、角色/别名与分支图等**已有可信语义索引**判断真实连通世界，不能仅以不同 UUID 判为不同世界。若没有可信索引，保持 `false`。
2. `r50_protected_clear`：仅对 R50 的**许可保护世界元数据名单**核对世界重叠，不能读取 R50 测试题目、故事正文、回答等。
3. `prior_sft_clear`：以已曝光 Train/Val/Dev 的世界关联索引或经认可的来源指纹对比；旧模型输入/被训练过的世界不可误做新独立测试数据。
4. `r55_r57_dev_clear`：对 R55/R57 的开发题/世界元数据核对。其内容不得冒充新独立训练评价题。
5. `other_protected_clear`：检查剩余 embargo、保护或保留世界。

**未找到独立可复核的证明时，不得将任何一个 `false` 改为 `true`，也不得造 `evidence_reference`。** 审核需为真实世界分量赋予私有 `world_component`，并保留可验证的私有证据路径/版本记录。即使五项都为真，也只是 Owner 申明/待独立验证，不等于 G1 自动 PASS。

对已独立核实的世界，之后才允许将私有队列（去掉多余字段也可）作为 `pilot_round1_shortlist.py --guards ...` 的 guard registry 使用，并保留 `__INDEPENDENCE_REVIEW_PENDING`。此时对 Assistant 正文的任何小批量导出仍需另行按 G2 范围门禁核准。

## 当前状态

`R58_ROUND1_METADATA_DISCOVERY_1280_PASS__G1_PRIVATE_REVIEW_QUEUE_PENDING`

- 元数据发现 1280：**PASS（Owner 实测）**
- G1 保护世界与历史训练曝光：**HOLD（未有独立证据）**
- G2 历史 Runtime / G3 双 Reviewer：**HOLD / NOT_STARTED**
- Train / Validation / Teacher：**0 / 0 / 0**
- 首轮上限：**5 语义世界 / 20 候选回复**
- 首轮完成提醒条件：`R58_ROUND1_PILOT_COMPLETION_SAFE.json` 顶层必须为 `R58_ROUND1_PILOT_REVIEW_COMPLETE`；完成前不提醒，Owner 未批准前不扩样。
- Skill v0.1 不修改，PR #7 Draft，不访问 R50 正文、不修改生产库、不触发 HF CPU/GPU。
