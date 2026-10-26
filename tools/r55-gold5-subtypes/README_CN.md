# StoryForge R55 Gold5 — 硬规则子类型复核（只读辅助诊断）

截至 2026-10-26，仅用于**已经冻结的旧开发集**，不是独立 Held-out，也不是模型整体错误率。该补充标注由 AI 辅助阅读已完成裁决的原文和理由提出，**不是新的裁决/正式人工语义认证**。

## 输入

- `R55_GOLD5_FINAL_EVIDENCE_OWNER_DOCKET_PRIVATE.json`：原始 76 候选私有卷宗
- `R55_GOLD5_FINAL_EVIDENCE_DECISIONS_ALL_152_COMPLETED_PRIVATE.json`：原始 152 条冻结裁决
- `R55_GOLD5_HARD_RULE_SUBTYPES_OWNER_PRIVATE.json`：本次新提出的 62 条已确认硬规则子标签、4 条 HOLD 证据缺口（**私有，另存本地，不入 Git**）

## 运行

在脚本所在目录中运行，例如：

```bash
umask 077
ROOT="$HOME/.local/share/storyforge/r55/gold5-dev20"
python3 v03_r55_gold5_rule_subtypes.py \
  --docket "$ROOT/final-evidence-v1/owner/R55_GOLD5_FINAL_EVIDENCE_OWNER_DOCKET_PRIVATE.json" \
  --decisions "$ROOT/completed/final-evidence/R55_GOLD5_FINAL_EVIDENCE_DECISIONS_ALL_152_COMPLETED_PRIVATE.json" \
  --subtypes "$ROOT/diagnostics/R55_GOLD5_HARD_RULE_SUBTYPES_OWNER_PRIVATE.json" \
  --out "$ROOT/diagnostics/R55_GOLD5_RULE_SUBTYPES_SAFE_COUNT_ONLY.json"
```

成功提示：`R55_GOLD5_RULE_SUBTYPES_DIAGNOSTIC_SAFE_PASS__NO_FINAL_RECLASSIFICATION__NO_R50`。如果 `--out` 已经存在，该工具拒绝覆盖。

## 分类定义（主标签，互斥）

- `player_psychology_or_intent`: 代写玩家想法、恐惧、认识、掩饰动机等；不自动构成严重自主权侵犯
- `player_action_or_speech`: 代写玩家行动/语言；不自动构成严重自主权侵犯
- `user_event_continuity`: 否认或替换用户已经明确执行的动作/事件
- `character_identity_or_relation`: 未获授权的姓名或确定身份关系
- `world_timeline_age`: 年龄、历史经历、年表矛盾
- `forbidden_phrase_exact`: 明确禁止的字面禁句
- `forbidden_phrase_semantic`: 禁句近义表达；**高风险人工再核验**
- `forbidden_user_echo`: 禁止复述玩家原话的故事规则
- `forbidden_echo_question`: 复述用户触动词后直接加问号
- `dialogue_language_format`: 韩语原文（中文翻译）双语格式限制

**注意：主标签仅选最有代表性的一项，同一回复仍可能有其他问题。所有标签和四项 HOLD 均保持原始裁决不变；本工具无训练/模型推理/GPU/R50 逻辑。**

## 质量边界

本工具验证 76 条 token 顺序、152 条原始裁决计数、62 硬规则 confirmed、4 硬规则 HOLD、源码 SHA256、补充分类枚举和原始证据字段逐字一致。不重新运行原始三轮仲裁或判断证据真实性。

在将这些标签用于 v0.3-B 数据策略之前，建议对 near-phrase、引用用户话语但不是 NPC 台词的格式问题等高争议记录进行额外人工抽查；HOLD 缺少新增事实时保持 HOLD。不要把旧 DEV20 题目当作新测试集。
