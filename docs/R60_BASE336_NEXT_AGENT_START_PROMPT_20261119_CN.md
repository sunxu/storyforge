# R60 Base336 P2 Quality-v1：2026-11-19 旧 Agent 提示词（已归档，请勿执行）

**本文件是历史入口，不再作为现行 Agent 提示词。** 2026-11-19/20 旧指令中的“Gold48 未生成 / Owner 未冻结 / 必须补完整历史保护集全集 / 只做两臂 / 四模型只是建议 / 没有真实原始回答”等表述，已经被后续 Owner SAFE 与冻结决议覆盖。原历史内容可从 Git 版本历史查询，不在此重复，以免新 Agent 误执行。

## 唯一现行提示词（2026-11-21）

**[直接阅读、复制：R60 Base336 Gold48 新 Agent 启动提示词](R60_BASE336_NEXT_AGENT_START_PROMPT_20261121_CN.md)**。

当前已完成 Gold48 **48 主分析 / 42 敏感性**受限范围 Owner 冻结、**四模型 Generation Profile** 独立冻结，HF CPU Tokenizer 回执与合成 CI 已通过。尚缺 Qwen3.8 + PEFT 的实际 GPU 运行时及三个历史 LoRA SHA 精确绑定；`inference_authorized=false`。**无需重复构造数据、重复历史来源审计、重跑 HF CPU Job、重复开发生成/Token/HF 核心。**

正式可追溯任务、状态和停止边界以 [主线交接任务书最顶部](R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md) 和 [AGENTS.md 最顶部](../AGENTS.md) 为准；先核验 PR #31 实时 HEAD 与 CI，不从上述历史文件名推断其内容版本。
