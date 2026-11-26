# StoryForge v0.3 — 新对话交接说明（R51 Gold195 主线）

**交接日期：** 2026-10-19  
**项目：** 私有 `sunxu/storyforge`  
**审计分支：** `audit/r49-r50-source-intake-20261015`  
**Draft PR：** https://github.com/sunxu/storyforge/pull/2（仍开放、未合并）  
**交接准备时 HEAD：** `9dae20b750ac74f01fa167810d8d8e0340fc011a`（新对话须重新核验，提交此包后 HEAD 会变化）  
**工作切换：** R50 W17 停止重复审计，优先推进 **R51 Gold195 训练候选准入**。

## 1. 初始目标与偏航纠正

目标是为 `Qwen/Qwen3.8-27B` 训练、评测中文互动小说模型，使剧情/人物保持连贯、禁止替玩家做决定、兼顾文学表现与 NPC 推进。R50 消耗了过多时间审查同一 W17 证据，反复 7/7 `INSUFFICIENT_CONTEXT`，已触及证据边界。不要把“复原平台历史运行时请求”误作“构建可信的、统一的独立模型测试输入”的唯一途径；但也不能把较晚的角色卡冒充历史生效事实。

**工作策略：** R50 遇到 W17 新源证据才恢复；R51 无需等待 R50 全部关闭即可开展，按照 2026-10-14 R49–R57 阶段计划，R51 只依赖 R49。之后 R52 数据单变量实验预注册，R53 CPU collator，R54 显式授权 GPU，R55 开发回归，R56 一次性独立盲测，R57 仅根据预先约定门禁决定晋升或 HOLD。

## 2. 已完成的训练与评测

| 阶段 | 真实结果 | 边界 |
|---|---|---|
| v0.1 | 基线模型训练/两轮独立盲审完成；Round1 Base 13 / Adapter 7；Round2 10/10 | 工程 PASS，不证明模型稳定胜过 Base |
| R39–R45 | Gold195 来自87+108；旧实验候选 Train49 / Val15；另有 18 HOLD | 49/15 仍非正式 R51 训练准入 |
| R46 | A100-80GB 探索性 SFT，7 optimizer steps；train loss 1.92598、val loss 1.74831；adapter SHA256 `bec4ba74d858db3ff117d581478ef9cac41b1ecc7ea2a67523f6db1096addf2b` | 训练重载工程 PASS，未晋升 |
| R47 | 20组三回复：v0.2 11 / Base 5 / v0.1 4 多数胜 | 已暴露，仅开发诊断 |
| R48 | 20组四回复：Gold 8 / v0.2 7 / v0.1 3 / Base 2 | 已暴露，不能当新盲测 |

权威计划：`docs/plans/StoryForge_v03_Test_and_Training_Gates_20261014.json`（仍为 `PROPOSED_NOT_YET_APPROVED`）；四臂输入契约：`docs/plans/V03_R50_FOUR_ARM_INPUT_CONTRACT_DRAFT_20261016.md`（DRAFT，未批准）。

## 3. R51 最新真实来源验证（本次交接最重要）

**已由 GitHub 专项 CI 正式通过：** [Gold195 Original Readiness (no GPU) #39233810359](https://github.com/sunxu/storyforge/actions/runs/39233810359)。相关最新收据：`docs/evidence/V03_R51_GOLD195_REAL_GIT_PREFLIGHT_20261019.json`；截至准备此包的 commit `9dae20b`。

- Gold87：`evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl`，原 Git blob SHA1 `a2038e18bee8ddef96b93bb6746270a462f9a6e4`。
- Gold108：`evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl`，SHA256 `27d15b6f8baf7935ee2c48f85558adc3b5b25e3558e127485d0f17b620f80308`。
- 195 个互异候选 ID、195 个原始最终 Assistant 目标、195 个目标 SHA 匹配、1909 个历史消息记录（每条3–12条）。
- 13 个互异来源故事 ID；07、11 故事没有选入 Gold。**不同 ID 不自动证明语义世界完全独立。**
- **仍为 0 Train / 0 Validation 正式准入，split 全部 null；没有派生 train.jsonl**。
- 171 条明确具有导出/目标角色卡 `UNVERIFIED` 一类标记；22 条缺少检查范围内的原始来源索引字段；10 条 Gold87 标注来源人物年龄 `UNSPECIFIED`。三类统计可能重叠，未标记样本也不是自动 PASS。
- 部分 Cohort108 使用不同源元数据字段：3 行 `source_story_id` fallback；目标 hash 字段存在三种写法。**不要修改来源行以统一字段。**
- 此项 CI **不等于**原始完整聊天归档逐行重放、内容/权益/时间点/别名/玩家自主权审查或实际 Qwen loss-mask/collator 验收。

已在 GitHub：
- `scripts/v03_r51_gold195_readiness.py`（只读汇总，不输出原文）
- `tests/test_v03_r51_gold195_readiness.py`
- `docs/plans/V03_R51_GOLD195_CONTEXT_ONLY_ADMISSION_NEXT_20261019.md`
- `docs/plans/V03_R51_GOLD195_READINESS_20261019.md`

## 4. R51 下一阶段：私有、逐条、源锚定准入

在不改 Gold195 原件的前提下，为每个候选做**多标签**分流并保留来源证据：
1. `CONTEXT_ONLY_POSSIBLE__HOLD`：若经原文核实只靠连续历史对话即可构成真实训练输入，避免强制追索不必要的历史卡；仍要做安全、权益、世界划分、时间点检验；
2. `CARD_OR_LONG_RANGE_SOURCE_REQUIRED__HOLD`：当前上下文不足以支持目标中的人设/关系/长期禁令，需要历史卡或更早规则，不能虚构；
3. `CONTENT_OR_RIGHTS_HOLD`：年龄、同意、版权/许可、玩家控制、越权创作或独立评分证据不足；
4. `SOURCE_POINTER_RECONCILIATION_HOLD`：原件中缺少或不一致的来源消息序号，需要经认证原始档案来核实。

准入工作底稿只能是**新的私有版本化文件**（`~/.local/share/storyforge/.../`，mode 0600），建议每条保留候选 ID、目标 SHA256、证据引用、确定的缺口、审阅结果、是否依赖历史卡、是否可用 context-only 输入契约、年龄/权利/玩家自主权结论。不以未证实的事实给出 PASS。只有完成世界关联组件划分及与旧暴露测试和 R50 的防重合核验，才能规划 component-disjoint Train/Val。**120–160 是目标建议，不是必须凑齐的配额**；旧 R45 HOLD18 不得擅自加入。

可在审核路径设计和风险统计方面立即动手；若涉及实际私有证据全文，请用授权本地原件而非空想来源。不要把真实故事文本贴到普通 Git/CI。

## 5. R50 W17 冻结分支，不得误认为已经解除

R50 原始50题筛后保留46：W16=9、W17=10、W18=9、W19=8、W20=10。冻结测试题不能训练、改写、自动 seal 或用于泄漏式调参。

W17 与旧 02/04/10 的三组初始关联结论 `INSUFFICIENT_EVIDENCE`。后来七项独立 AI 分流先审局部片段、再审344条完整消息档案记录，引用75条，最终仍 **7/7 `INSUFFICIENT_CONTEXT`**。W17 26次来源引用对应16条不同消息，全部有时间戳且位于聊天窗口内；导出卡记录最近编辑早于第一条聊天，但当时真正投入模型的角色卡/规则/掩码仍 **NOT_CERTIFIED**。W17 来源卡内容版本记录0，审核快照0；旧04↔07关联组件仍存在。

W17 关键文件及 SHA256：
- `docs/evidence/V03_R50_W17_FULL_MESSAGE_AI_REVIEW_OWNER_RECEIPT_20261019.json`
- `docs/evidence/V03_R50_W17_TIMEPOINT_METADATA_OWNER_RECEIPT_20261019.json`
- 本地七项完整来源清单 `189f84e0e2891499723ba7e9e14cc866c057c9ab5ead727ff4c192e717510476`
- 本地最终全消息审核工作底稿 `6482dd02b27d80f72763b23b848cf7c0b2765853f09ef0beb2ae4961d50b7ce3`
- 补新证据方案 `docs/plans/V03_R50_W17_NEW_SOURCE_EVIDENCE_ACQUISITION_20261019.md`

**STOP：** 没有新的平台请求快照、历史角色卡/覆盖配置或可信跨世界关联证据，就不再反复运行同样的 W17 AI 审核。R50 保持 `SEMANTIC_HOLD`、`NO_FINAL_SEAL`。Draft PR #2 不得自动 merge。

## 6. 下一对话的具体行动顺序

- **先核对最新 PR #2 HEAD/CI**；本交接引用 `9dae20b` 为准备时状态，交接提交会使 HEAD 再推进。不要把 R51 已有真实来源预检误作“尚未开始”。
- 读 Gold87/108 的选择 README、原始 metadata schemas 与 [R51 context-only 准入方案](../plans/V03_R51_GOLD195_CONTEXT_ONLY_ADMISSION_NEXT_20261019.md)，列出可从已有受控材料验证的每条审计字段。
- **优先复核可直接影响实际训练价值的风险**：年龄/同意/权益、对玩家行动与心理代写、后验卡污染与长期人设承诺、重复样本/关联世界隔离；将判定绑定真实来源。
- 构建最小且不泄漏私有文本的准入报告/复核工作底稿；有内容证据才批准。对无法核实的来源序号或卡版本保留 HOLD。
- 在完成真实每行审查后，才评估是否可以从已准入世界组件划分 Train/Val；准备 R52 单变量数据实验。R53 前需实际 Qwen tokenizer/Collator mask 复核，R54 GPU 需要用户另行明确付费授权。

## 7. 常用核验命令（无 AI/GPU）

```bash
cd ~/workspace/storyforge
git fetch origin audit/r49-r50-source-intake-20261015
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only

python3 -m unittest discover -s tests -p 'test_v03_r51_gold195_readiness.py' -v
python3 scripts/v03_r51_gold195_readiness.py --repo .
```

成功标记 `R51_GOLD195_SOURCE_INTEGRITY_PASS__TRAINING_ADMISSION_HOLD`。这些命令复核原始完整性，**不会**产生已获准的 Train/Val；不要误以为需要不停重跑预检。此前全仓通用 CI 仍有既有 Ruff 问题，须区分专用 no-GPU CI 与通用 CI 的结果。

## 8. 必须遵守的权限与质量边界

1. 不修改 Gold87/108、195 原件、R45 Train49/Val15、18 HOLD、R50 46题、历史 adapter SHA 或冻结基线。
2. 不上传私有故事/审阅理由/测试答案映射到普通 Git；只写脱敏摘要、证据摘要、合成测试、审核工具与明确的 HOLD。
3. 不自行运行付费 GPU/HF 或批量模型生成，不晋升模型，不批准输入契约，不 merge，不做最终 seal。
4. R47/R48 仅作开发诊断，不能当新独立盲测；v0.3 实验必须是数据单变量比较。
5. **以模型质量提升为主轴，避免为了审计而审计。** R51 产生可用的候选集/明确的阻塞原因，比连续新增形式化验证器重要。

**交接完成判定：** 新对话准确识别 `GOLD195_ORIGINAL_INTEGRITY_PASS__TRAINING_ADMISSION_HOLD`，先开展逐条准入分流，停止 W17 重复 AI 审计，不越权训练/合并/封存。
