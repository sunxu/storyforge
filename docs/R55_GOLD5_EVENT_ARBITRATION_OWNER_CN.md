# StoryForge R55 Gold5 v2 — Owner 本地逐事件盲仲裁

**阶段：R55 三轮 Pair/Four/Five 已完成本地 SHA 冻结与解盲汇总，但真实问题未完成仲裁。**

本工具是 CPU/stdlib 的私人审查包生成与逐条审核回执校验器，不使用 R50、不调用模型、不启动 HF Job、不更新既有数据。它依赖已经应用到本地项目的 `scripts/v03_r55_gold5_owner_unblind.py` 与 `scripts/v03_r55_gold5_review_freeze.py`。

## 一、原则

1. **以 (原题、原候选回复) 汇总重复标记，不等于对事实事件自动去重。** 同一个回复中可能包含多个问题；Reviewer 原始记录可能重复指向同一事件、也可能描述不同事件。需要仲裁者阅读原文后自行判断。生成的 `candidate_token` 是随机匿名 ID，不是模型身份。
2. **不向仲裁者提供解盲身份和旧 Reviewer 结论。** 提供的盲审包包含故事规则、历史、当前输入、候选回复，每个候选需要分别判定 `agency` 玩家自主权和 `hard_fact_or_ban` 明确禁句/硬事实。即使只在其中一类被旧 Reviewer 标记，也必须判断两类。为降低既有评分的锚定效应，Reviewer 证据另存 `coordinator/`，只供 Owner 做第二阶段冲突复核。
3. **默认 `--scope flagged`**：只审查三轮中至少一位 Reviewer 标记的问题候选。这个集合具有选择偏差，结果不能直接解释成模型在全部题上的无偏严重问题率；如果需要完整逐候选仲裁，可首次执行时选择 `--scope all`，覆盖 20×5=100 个候选。这是同一批 20 道旧开发题，不是 100 道独立测试题。
4. 源正文、输出包、证据索引、Reviewer 决策全是私人材料，**不得提交 Git、公开发到聊天或跨 Reviewer 传播答案映射**。若打算把盲包送给远端 AI Reviewer，需 Owner 自行决定允许该服务处理私有小说内容。
5. 原始 Gold 仅是第五份历史参考，不等于第五个模型，也不享受违规豁免。v0.3-A checkpoint-16 当前 R50 NO-GO 不受本工具自动更改。

## 二、安装代码并运行合成测试

```bash
set -euo pipefail
cd ~/workspace/storyforge

git apply --check ~/Downloads/StoryForge_R55_GOLD5_EVENT_ARBITRATION_NOJOB_20261023.patch
git apply ~/Downloads/StoryForge_R55_GOLD5_EVENT_ARBITRATION_NOJOB_20261023.patch

python3 -m unittest discover -s tests -p 'test_v03_r55_gold5_event_arbitration.py' -v
```

测试纯合成，不会接触真实故事或 R50。确认新增脚本/测试/中文指南的差异后，只添加这三个路径到 Git；不要使用 `git add -A`。

## 三、在 Owner Mac 上生成**真实**私有仲裁包

```bash
set -euo pipefail
umask 077
cd ~/workspace/storyforge

ROOT="$HOME/.local/share/storyforge/r55/gold5-dev20"
ADJ="$ROOT/event-arbitration-v1"

python3 scripts/v03_r55_gold5_event_arbitration.py \
  --mode prepare \
  --pack "$ROOT/owner-pack-v2" \
  --pair-dir "$ROOT/frozen/pair-v1" \
  --four-dir "$ROOT/frozen/four-v1" \
  --five-dir "$ROOT/frozen/five-v1" \
  --scope flagged \
  --out-dir "$ADJ"

cat "$ADJ/safe/R55_GOLD5_ARBITRATION_PREP_SAFE_COUNT_ONLY.json"
```

成功标记：

`R55_GOLD5_ADJUDICATION_PRIVATE_PACK_PREPARED__NO_CONFIRMED_EVENTS__NO_R50`

失败标记：`R55_GOLD5_ARBITRATION_HOLD__...`，仅报告错误码。该命令重新严格校验九份真实冻结 CSV、三个收据和 Owner 私钥 SHA 对应的匿名回复（发生错误会拒绝创建包）。`$ADJ` **不能提前存在**，也不能在仓库内。

### 输出内容

- `reviewers/R55_GOLD5_ARBITER_BLIND_ITEMS_PRIVATE.json` — 仅匿名原文、候选回复、两个待判类别。给**新的独立仲裁者**。
- `reviewers/R55_GOLD5_ARBITER_DECISIONS_BLANK_PRIVATE.json` — 同一顺序的待填写 verdict 模板。请仲裁者填写，而非让 Owner 根据历史模型结果代填。
- `coordinator/R55_GOLD5_ARBITRATION_SOURCE_INDEX_PRIVATE.json` — **绝不发给仲裁者**，含真实 arm 身份、Case 索引、SHA256、三轮原始 Reviewer 问题证据。保留于 Owner Mac。
- `safe/R55_GOLD5_ARBITRATION_PREP_SAFE_COUNT_ONLY.json` — 不含原文或案例 ID，可将此 JSON 发回 ChatGPT。

## 四、仲裁判定标准

每个匿名候选必须对两类分别填写：

- `CONFIRMED`：有直接可见的严重玩家决策代写/明显违反冻结规则，需提供从候选回复中逐字引用的 `candidate_quote`，以及从冻结规则/历史/当前用户输入中逐字引用的 `context_quote`，并给出具体原因。若找不到可见原文证据，不得确认。
- `REJECTED`：针对该类别不成立，例如角色强制**剧情内 NPC**行为并不等于未经用户允许替玩家做出重大决策；需写出有根据的驳回理由。
- `HOLD_INSUFFICIENT_EVIDENCE`：信息不足或源时间点矛盾，说明缺什么，不得猜测补证。任何成人/年龄/同意或特殊设定若目标时间点不可证，须按原可见内容谨慎判断。

`rationale` 至少 12 个字符，不能空。`CONFIRMED` 的两种引用都必须是冻结原文的**原样子串**；程序将校验引用存在，不会自动代替人类评判引用是否足以支持结论。一个候选可能出现多个独立事件；如需逐事件清单，请在 rationale 中分项说明，必要时另外补充人工仲裁表，不要把程序输出的一组 CONFIRMED 自动解释为唯一事件数。

**不要让同一聊天会话兼任 Owner（掌握解盲映射）和“独立盲仲裁者”。** 已看过 R55 统计与模型身份的聊天不能构成新独立盲审。

## 五、收回仲裁者填写的 JSON 后校验

Owner 保存仲裁完成版至私人、非 Git 的文件，例如：

`$ROOT/completed/arbitration/R55_GOLD5_ARBITER_DECISIONS_COMPLETED_PRIVATE.json`

运行：

```bash
RESULT="$ROOT/event-arbitration-validated-v1"
python3 scripts/v03_r55_gold5_event_arbitration.py \
  --mode validate \
  --pack "$ADJ" \
  --decisions "$ROOT/completed/arbitration/R55_GOLD5_ARBITER_DECISIONS_COMPLETED_PRIVATE.json" \
  --out-dir "$RESULT"
cat "$RESULT/R55_GOLD5_ARBITRATION_DECISIONS_SAFE_COUNT_ONLY.json"
```

输出：

- `R55_GOLD5_ARBITRATION_DECISIONS_PRIVATE.json`：Owner 专用，关联匿名 ID 与真正 arm，不对外发布。
- `R55_GOLD5_ARBITRATION_DECISIONS_SAFE_COUNT_ONLY.json`：无私人故事文本和案例 ID，只报告经模板/引用字节校验的 verdict 数量；**不自动证明裁定正确、评审独立或模型可靠**。

**完成时才能**使用此 SAFE_JSON 做后续模型问题归因。已知的 R55 原始质量结论仍是 v0.3-A 的 Pair 10/10，六维均分 v0.3-A 低于 v0.2，R50 NO-GO。不要为此重跑旧 GPU 推理。
