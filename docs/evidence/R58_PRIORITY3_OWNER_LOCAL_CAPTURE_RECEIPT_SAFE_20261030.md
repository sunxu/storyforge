# R58 Priority3 — Owner 本机捕获回执（SAFE，2026-10-30）

本轮 Owner 在 Mac 上执行了私有 SQL → `capture_priority3.py` 的实际捕获以及 SHA256 文件级复核，并在对话中报告：

```text
{"records": 3, "runtime_byte_exact_pass": 0, "status": "PRIVATE_CAPTURE_COMPLETE_NOT_TRAIN_ADMITTED"}
R58_SOURCE_CAPTURE: PASS
SHA256_VERIFICATION: PASS
SOURCE_RECORDS: 3
TRAINING_ADMISSION: HOLD
```

**结论：`OWNER_LOCAL_SOURCE_CAPTURE_SHA256_PASS`，证据级别为 Owner CLI 回执；本助手没有直接访问本地私有源包及 manifest，不能升级为独立核验。**

- 完成了三条来源记录的 Mac 本机私有捕获，并由用户脚本确认来源文件与私有 manifest 的原始文件级 SHA256 一致。
- 该步骤保留包含真实 story/session/message ID、目标回复、批准卡和 24 条历史消息的本机私有文件。**GitHub 和 ChatGPT 不保存这些私有记录、物理 ID 或单条哈希**。
- SQL 查询只读；无数据库写入，未使用 HF Job，未打开 R50。尚未验证已备份到 HF 私有 Bucket。
- 训练准入仍为 **Train=0 / Validation=0**，Prompt 字节级一致性 `0 PASS / 3 HOLD`，Skill v0.1 保持不变。
- **禁止**为补强证据而悄悄重跑数据库并替换源包；以本次本地捕获为此轮固定物理来源记录，下一步继续离线复原与证据门禁。

## 新增离线复核门禁（代码已提交，尚待 Owner 执行）

- `experiments/r58_roleplay_replay/verify_priority3_private.py`：独立对照私有原始 JSONL 与 manifest 的文件大小、文件 SHA256、三种来源/物理 ID 唯一性、完成标记、私有文件权限，并逐案重算来源卡、检查点、24 历史及目标回复 **4 × 3 = 12 个指纹**。只输出 PASS/HOLD 汇总，不输出私有 ID、内容和 digest。
- `experiments/r58_roleplay_replay/test_verify_priority3_private.py`：新增 9 条纯合成离线测试，覆盖合法样本、正文被修改、文件 hash 被同步修改但逐案 hash 不符、逐案 hash 被修改、完成标记缺失、符号链接、权限、manifest ID 不一致。**尚未执行新 9 项测试**。
- 正式运行须先在 Mac 本地完成合成测试，再用 `--private-dir` 指向首次已固定的本机隔离目录；不得重新执行私有 SQL。

## 保留 HOLD

实际线上代码部署版本、请求时 locale / model / relay 参数、完整 System Prompt、记忆/RAG/导演等动态依赖、请求字节哈希/逐项来源以及语义世界与 R50 保护集隔离均未认证。私有捕获通过**不等于训练数据准入**。
