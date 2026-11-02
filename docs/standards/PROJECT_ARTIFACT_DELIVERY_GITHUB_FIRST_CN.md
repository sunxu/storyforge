# R58 工具交付渠道规范（GitHub 优先）

生效：2026-11-02。适用范围：StoryForge 项目中的工具代码、测试、运行手册、SAFE 统计报告和交接材料。

## 默认交付

- **代码、测试、规范和可公开 SAFE 回执统一以 GitHub 分支/PR 交付**，提供文件路径、commit SHA、测试情况和 PR 链接。优先复用既有仓库模块，而不是制作另一个脱离仓库的 ZIP 原型。
- 交付前检查 `AGENTS.md`、仓库当前 HEAD、已有工具/测试；对新脚本进行合成测试、静态检查。未执行的检查须标记为未验证，不得声称 PASS。
- **ZIP 仅在用户明确要求压缩包、离线传输或完整跨环境交接时创建**。先前 R58 详细交接 ZIP 来自用户对该次交接的明确要求，**不是以后交付脚本的常规规定**。
- Github 无法写入时明确报告障碍，暂存本地修改及说明；不要以 ZIP 替代 GitHub 已完成交付的说法。
- `main`、PR 合并、历史冻结资产、训练/GPU、付费任务继续受独立授权和项目门禁约束。

## 公开/私人边界

- PRIVATE 剧情正文、世界卡、审核逐案结果、稳定 case ID/UUID 映射、逐案哈希、未发布模型输出、R50 保护材料等只能保留在受控私人存储。
- 可入 GitHub：不泄漏私人值的 SAFE 聚合计数、固定状态码、脚本、合成 canary 测试、无敏感内容的使用文档。
- 需要逐案例补审清单时，工具应在私人目录以新文件、0600 权限输出，不提交 GitHub。

## 现行 R58 历史证据复用

工具：`experiments/r58_quality/legacy_gold_target_reuse.py`。它按 `story_id / story_uuid + target_sha256` 进行**目标级**绑定，不证明上下文没有变化，不提供六维 Quality-v1 PASS，也不替代 `gold108_review_binding.py` 对历史五维双审证据的更严格核对。

- Gold87 索引：`evaluations/v0.2/gold-quality-87/gold_87_index.csv`，哈希字段 `sample_target_sha256`。
  - 该冻结文件实际含两行固定解析标记：`<PARSED TEXT FOR SHEET: 1 / 1 TABS` 和 `TAB NAME: gold_87_index.csv>`。解析器只识别这两个精确前缀，不改写原文件；不符合合同返回 `LEGACY_87_WRAPPER_INVALID` HOLD。
- Gold108 索引：`evaluations/v0.2/gold-quality-108/gold_108_index.csv`，哈希字段 `target_sha256`。
- Gold108 双审证据：`evaluations/v0.2/gold-quality-108/dual_accept_review_evidence_108.jsonl`。
- 任务：`$HOME/.local/share/storyforge/r58/gold195-review-tasks-v1.jsonl`，本地私人文件，不上传仓库。

执行示例（本地仓库根目录）：

```bash
python3 experiments/r58_quality/legacy_gold_target_reuse.py \
  --repo-root "$PWD" \
  --gold87-index evaluations/v0.2/gold-quality-87/gold_87_index.csv \
  --gold108-index evaluations/v0.2/gold-quality-108/gold_108_index.csv \
  --gold108-evidence evaluations/v0.2/gold-quality-108/dual_accept_review_evidence_108.jsonl \
  --private-tasks "$HOME/.local/share/storyforge/r58/gold195-review-tasks-v1.jsonl"
```

默认只打印 SAFE JSON，未跑实际 PRIVATE 数据时不得给出真实匹配率。追加 `--private-queue-output "$HOME/.local/share/storyforge/r58/legacy-reuse-queue-v1.jsonl"` 可在私有目录写新建的逐案分流清单。注意它是**补审候选分流**，不是已经证明最小的六维重审数量。

当前脚本为 scoped prototype：仍需测试目录和权限等恶意输入边界，Gold87 仅完成索引审核状态读取，Gold108 的基本证据绑定不替代现有严格评分验证。状态只能是 `TARGET_IDENTITY_TRIAGE_ONLY__SEMANTIC_HOLD`。不启动 HF/GPU/训练。
