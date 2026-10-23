# StoryForge R50 — 12 条连续 User 消息的 Owner 本地回放审核

**任务阶段：** R50 46 条 PRESEAL 候选，尚未准入正式 Held-out；本程序不批准评估合同、不执行模型推理、不训练、也不读取开发用 R55/R56 题目。

## 审核依据（来自项目已存在的实现，而非通用猜测）

- `audit/r49-r50-source-intake-20261015:scripts/v03_r50_cpu_tokenizer_preflight_46.py`，Git blob `c546194bd02608e921d9c673fa3e549c022468ae`，其中的 `make_messages(case, system_text)`：System + 世界卡 + 长期规则，接原历史消息（角色和顺序不变），最后再追加一条 User。**不合并连续的 User 消息。**
- 同一分支的 `docs/evidence/V03_R50_46_CPU_TOKENIZER_VERIFIED_20261016.json`：原始 46 条 / 364 条历史 / 12 条以 User 结尾；这属于历史独立 HF CPU 运行记录，不是 2026-10-22 新 Job 的报告。
- **当前新 Job** `6ada3f1d925af0e27d4f569f`，`r50-cpu46-20261022T164410Z-305591`；Owner 本地报告 SHA256 `56aeac340ac1c0be1d0000314bcbdc72abd2f59582d643eee9e50698529f748e`；Owner intake 文件 SHA256 `9b922c53cdafab11bd523e9c70f71a66a45d631da2b033487f2320b4150fe781`。

这次本地审核逐条比较 **冻结的 46 条数据与当前真实 Tokenizer 报告**：历史条数、连续 User 标志、真实 encoded-ID 摘要是否存在、Token 长度与预算记录；独立重放草案 `make_messages()`，确保无本地构造层的角色合并和顺序变化；核对固定 Qwen Tokenizer/Chat Template 文件哈希。

**限制：** 只有结构和编码成功，不代表 12 条 User→User 在文学交互上有一致的解释，也不代表 Base/v0.1/v0.2/v0.3-A 四个实际推理运行环境完全一致。这两项继续 HOLD。

## 执行（Mac 无须 Transformers）

在已更新的 StoryForge Git 仓库中：

```bash
set -euo pipefail
umask 077
cd ~/workspace/storyforge
python3 -m unittest discover -s tests -p 'test_v03_r50_role12_owner_audit.py' -v

RUN_KEY='r50-cpu46-20261022T164410Z-305591'
BASE="$HOME/.local/share/storyforge/r50/hf-cpu46/$RUN_KEY"

python3 scripts/v03_r50_role12_owner_audit.py \
  --candidates "$BASE/stage/private/R50_CANDIDATE_46_PRESEAL_PRIVATE.jsonl" \
  --system-file "$BASE/stage/private/R45_SYSTEM_CANDIDATE_64_OF_64_NOT_APPROVED_PRIVATE.txt" \
  --private-report "$BASE/results/R50_46_CPU_TOKENIZER_DRAFT_PRIVATE.json" \
  --owner-intake "$BASE/results/R50_CPU46_OWNER_INTAKE_COUNT_ONLY.json" \
  --output "$BASE/results/R50_ROLE12_OWNER_SAFE_AUDIT.json"

cat "$BASE/results/R50_ROLE12_OWNER_SAFE_AUDIT.json"
```

成功输出 `R50_ROLE12_OWNER_DRAFT_STRUCTURE_AND_ENCODING_COUNTS_PASS__NO_HF_JOB`。输出仅包含总数、SHA256 固定凭证及未关闭的 HOLD 状态，不输出任何故事正文、case ID、角色名、逐题 Token 计数、题目映射或模型回答。失败则退出码 2、仅打印允许的错误标记，不能以失败结果作 PASS，也不覆盖旧输出。**不要把私有的 46 条、System 或逐题报告提交 GitHub。**

## 验收门禁

- 通过：仅说明 **46/46 原冻结草案消息的原历史角色与顺序保留**、与 HF CPU 报告逐条字段一致、历史 User 结尾恰为 12、且 12 条在真实编码报告中都有 ID 摘要。
- 不通过：保持 `ROLE12_HOLD`，按本地错误标记查证，不重跑 HF Job。
- 即使通过，也不意味着四模型真实推理时模板完全一致，更不意味着 world semantic isolation、正式 seal 或 test admission 通过；`official_heldout_admitted=0`。
