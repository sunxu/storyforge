# R58 RolePlay→StoryForge SFT Skill v0.1

此目录是可移植的 **Skill 草案 + 已在合成数据上测试的离线工具**。它不会自动连接生产数据库、向 GitHub 写入、运行推理或启动付费 Hugging Face Job。需要安装到目标的 Skill 运行环境时，由 Owner 先检查 SKILL.md、SQL 和脚本；不要称其已安装或完成真实数据准入。

运行顺序（须在获授权的 Hugging Face 私有工作区运行脚本，**不要用 Mac/Docker 进行项目计算**）：

```bash
python scripts/r58_intake.py shortlist --input stories.csv --output selected_private.jsonl --limit 30
python scripts/r58_intake.py gate --input reviewed_private.jsonl --output decision_private.jsonl --safe-output decision_safe.json
python scripts/r58_intake.py freeze --input ready_private.jsonl --decision decision_private.jsonl --output-dir new-private-freeze-dir --world-graph-sha <SHA256>
```

`tests/` 只使用虚构数据，在沙箱环境可离线运行。

阶段差异：短名单无需正文；`gate` 需要外部完成的逐案证据，不替 Reviewer 判语义；`freeze` 仅冻结带完整已验证 System/历史的字节，不验证真实 runtime 本身。后续 HF CPU `collator` PASS 和 Owner GPU 授权属于额外门禁。
