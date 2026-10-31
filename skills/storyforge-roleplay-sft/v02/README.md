# StoryForge RolePlay SFT Skill v0.2 — G1/G2 只读预检（开发中）

该目录是 **v0.2 证据集成的第一阶段**，与已冻结 v0.1 的 `SKILL.md`、`MANIFEST_SAFE.json` 保持独立，不等于 Skill 正式升级、生产数据准入或端到端验收。

## 用途

- 从固定 Git blob 读取已有的四份 **SAFE** 证据，不读私有候选账本、R50 试题、训练正文、HF Bucket 或数据库。
- 将五个已知训练 Job 的**当前**文件哈希对账、首轮五故事／剩余四故事、R50 局部 UUID 排除与 G2 Provider 请求缺口合并显示。
- 严格识别 `G1=HOLD`、`G2=HOLD`、Train/Validation/Teacher=0、禁止扩样。任何来源缺失或有人把门禁改写为 PASS，退出码 42，不自动修复。
- 不把 v0.1 `gate` 中的自声明 PASS 布尔值视为权威证据；**不得使用该工具自动授权 v0.1 freeze**。

## 执行

在完整 Git 检出的 R58 分支执行（无需 HF、DB、GPU）：

```bash
python3 -m unittest discover -s skills/storyforge-roleplay-sft/v02 -p 'test_*.py' -v
python3 skills/storyforge-roleplay-sft/v02/r58_evidence_preflight.py --repo-root "$PWD"
```

该模块只负责证据一致性预检，**不是自动 G1/G2 清关器**。后续 v0.2 还需接入真正的候选级授权来源和运行时证据证书，以及只读 Supabase 数据合同；没有直接 request_id / Provider 输入字节证据时，必须继续 HOLD。

详见 `docs/evidence/R58_G1_G2_SKILL_V02_READINESS_MATRIX_SAFE_20261031.json`。这份矩阵只包含汇总计数和已公开来源引用。


## 新增：v0.2 受限流水线入口（尚非生产发布）

新增 `r58_pipeline_bridge.py` 与 `test_r58_pipeline_bridge.py`，不修改冻结的 v0.1.0 12 个文件。

这是**接口桥接预览，不是正式 `shortlist → gate → freeze` 的准入实现**：

- `shortlist` 读取 Owner 本地已有的元数据 CSV，执行与 Round1 一致的发现谓词：V2、approved、未删除、至少 50 条完成回复、至少 2 个 Session、有 world、有 character **或** characters、有 opening、且 source_type 为 original / dice_cocreate / ai_assisted；不再要求 director 或 genre。它只打印 SAFE 分类计数，**不会生成/替换候选清单，不重新挑选第五个世界，不读取故事正文**。
- `gate` 和 `freeze` 必须先经固定 Git blob 的 G1/G2 预检。当前返回 `HOLD_G1_G2_UNPROVEN__NO_V01_EXECUTION`（退出码 42），不打开私有候选输入、不调用 v0.1 命令、不生成任何数据。任何篡改或缺源也会返回 42。
- 所以 v0.1 仍保留为历史冻结的离线结构工具；**不能直接用 v0.1 的自声明布尔 PASS 作为正式 Dataset v0.4 准入**。
- 后续要接入的是真实可信的候选级证书及 Owner 审核记录，而非添加“可配置跳过 G1/G2”的开关。数据/保护来源索引或目标时点 Provider 字节证据缺失时继续 HOLD。

Owner 可在 R58 完整 Git 检出中运行以下纯本机测试（不使用 HF、不读取受保护内容）：

```bash
python3 -m unittest discover -s skills/storyforge-roleplay-sft/v02 -p 'test_*.py' -q
python3 skills/storyforge-roleplay-sft/v02/r58_evidence_preflight.py --repo-root "$PWD"
python3 skills/storyforge-roleplay-sft/v02/r58_pipeline_bridge.py gate --repo-root "$PWD"
# 上一条命令预计退出 42，这是门禁拒绝的预期行为
```

可选使用**已存在、已获准的本地元数据清单**进行纯 SAFE 计数（切勿上传清单到 GitHub 或聊天）：

```bash
python3 skills/storyforge-roleplay-sft/v02/r58_pipeline_bridge.py shortlist \
  --inventory "$HOME/.storyforge-r58-private/round1_pilot_20261030/EXISTING_INVENTORY.csv"
```

这里的 `EXISTING_INVENTORY.csv` 是占位名，需要替换为现有实际路径；**不得为此重新扫描数据库或开启新的抽样**。所有新增单元测试仅使用虚构行。隔离环境完成的 12 项新桥接测试 PASS，不代表 Owner Mac 的完整 24 项 v0.2 测试、G1/G2 真实证据检查或全仓 CI 已 PASS。首次本机运行后须单独归档 Owner SAFE 回执。
