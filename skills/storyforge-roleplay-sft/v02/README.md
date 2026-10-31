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
