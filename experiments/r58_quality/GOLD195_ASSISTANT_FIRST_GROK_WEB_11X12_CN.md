# StoryForge R58 — Assistant-first Gold132 / Grok 网页 11 批 × 12 条方案

Owner 明确授权最多 **132 条 Assistant-first Gold** 使用 Grok 网页审核，按 **11 批，每批 12 条**推进。授权外发不等于实际发送，脚本**没有**网页操作、网络调用、模型调用或自动上传。实际向 Grok 输入文件需由 Owner 在网页上逐案完成。GPU / HF 和训练准入仍禁止。

## 外发内容（每条审核包）

每个私人 Markdown 包含：匿名审核编号 `B01-01`—`B11-12`、完整原始 Assistant-first 历史、移除第一条 Assistant 的对照历史、当前 User、冻结 Gold 目标、导出时世界卡快照和严格 JSON 回答格式。**文件可能含完整的私人故事人物名、对白、世界信息**；匿名编号不能让正文匿名化。请在每次提交前检查世界卡中有无不必要的内部元数据、未来剧情信息或第三方隐私信息。当前导出工具不会自动删减世界卡内容，因为无损删减未经语义证明。

不得向 Grok 发送或向 GitHub 上传：真实 case ID、故事 UUID、源路径、SHA256、R50/heldout、其他无关候选或整份全量任务 JSONL。匿名标签到冻结来源的绑定仅保存在私有 `manifest.private.json`，这个 manifest **不要外发**。

## 第一步 — 只导出第 1 批

在 R58 Git 工作区根目录执行，所有私人数据保持在 Mac 上：

~~~bash
git pull --ff-only
R58_PRIVATE="$HOME/.local/share/storyforge/r58"

python3 -m unittest discover -s experiments/r58_quality \
  -p 'test_gold195_assistant_first_grok_batches.py' -v

python3 experiments/r58_quality/gold195_assistant_first_grok_batches.py \
  --repo-root "$PWD" \
  --private-comparison-input "$R58_PRIVATE/gold195-assistant-first-comparisons-v1.jsonl" \
  --private-full-tasks "$R58_PRIVATE/gold195-assistant-first-review132-v1.jsonl" \
  --batch 1 \
  --private-export-dir "$R58_PRIVATE/grok-af-batch01-v1"
~~~

预期 SAFE：`BATCH_PRIVATE_PACKETS_READY__NOT_SENT`、`batch=1`、`batch_size=12`、`private_files_written=13`。第 13 个是私人来源 manifest，不得发送给 Grok。默认不自动导出 batch 2–11。

新目录 0700、所有文件 0600，目录必须尚不存在；源文件与此前 Pilot10 不修改。每条 Markdown 必须在新 Grok 网页对话中独立提交，回复只取纯 JSON，在对应输出目录新建 `B01-01.json`…`B01-12.json`，文件权限 0600。**不可以用 JSON 模板占位答案冒充 Grok 结果。** 推荐同一 case 使用新会话，不提供其他审核者结论；不等于软件能证明审阅者独立性。

## 第二步 — 只读验收该批

~~~bash
python3 experiments/r58_quality/gold195_assistant_first_grok_batches.py \
  --repo-root "$PWD" \
  --private-comparison-input "$R58_PRIVATE/gold195-assistant-first-comparisons-v1.jsonl" \
  --private-full-tasks "$R58_PRIVATE/gold195-assistant-first-review132-v1.jsonl" \
  --batch 1 \
  --private-validate-dir "$R58_PRIVATE/grok-af-batch01-v1"
~~~

验收将重新核验全部 132 任务与来源绑定、batch01 manifest 和 12 份 Markdown 字节哈希，然后检查输出 JSON 的匿名标签、字段类型、判断枚举、首条 Assistant 逐字证据、可选 Gold/后续历史引用及论证长度。它**不能证明 Grok 判断语义上真实**。

出现缺失回复、格式错误、引用不在原文、主张截断但六项条件不成立、严重语义 HOLD，则 `BATCH_QUALITY_OR_EVIDENCE_HOLD`，禁止自动扩下一批。即使返回 `BATCH_VALIDATED__OWNER_GATE_REQUIRED`，也只是具备完整的结构化可核查材料，仍须 Owner 手工检查其判断质量。出现系统性误判、未来泄漏或严重硬事实冲突，应直接暂停后续外发。

## 第三步 — Owner 核验之后才导出下一批

仅在上一批 `BATCH_VALIDATED__OWNER_GATE_REQUIRED` 且 Owner 明确决定继续的情况下，允许在本地添加 `--owner-release-next-batch` 并提供上一批目录。例如第 2 批：

~~~bash
python3 experiments/r58_quality/gold195_assistant_first_grok_batches.py \
  --repo-root "$PWD" \
  --private-comparison-input "$R58_PRIVATE/gold195-assistant-first-comparisons-v1.jsonl" \
  --private-full-tasks "$R58_PRIVATE/gold195-assistant-first-review132-v1.jsonl" \
  --batch 2 \
  --previous-batch-dir "$R58_PRIVATE/grok-af-batch01-v1" \
  --owner-release-next-batch \
  --private-export-dir "$R58_PRIVATE/grok-af-batch02-v1"
~~~

3–11 批依次替换 batch N、上一批 N−1 的目录及新输出目录。脚本只接受上一批所有 12 条返回且无结构错误、无语义 HOLD；**任何后续批次也不会自动外发到 Grok**。

## 验收与安全门槛

- 抽取 132 个唯一 case，11 个不重叠 batch，每批固定 12；来源 Gold、世界卡和对照历史只读；
- Grok 推荐只有 `PRESERVE_LEADING_ASSISTANT_IF_RUNTIME_SUPPORTS`、`CONSIDER_DROP_ONLY_AFTER_EXPLICIT_FACT_REVIEW` 或 `HOLD_CONTEXT_UNRECOVERABLE`；只有真实引用支持才能构成初步建议；
- 即使是 `PROVISIONAL_DROP_REVIEW__NOT_APPROVED`，也不能直接截断训练输入；
- 如果保留完整 Assistant-first 历史可行，后续需单独进行 Qwen/ms-swift CPU collator/last_round 掩码验证；
- R50 保持封存，Quality-v1 准入 0，GPU/HF 不启动，PR #7 保持 Draft。

**已知限制：** 本工具不提供 Grok 网页自动化；引用字符串存在于原文不能证明其论证充分，Owner 仍需审查。浏览器发送内容之前需自行确认对应服务的数据保留规则。
