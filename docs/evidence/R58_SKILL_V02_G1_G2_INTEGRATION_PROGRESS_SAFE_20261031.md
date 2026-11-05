# R58 Skill v0.2 G1/G2 证据集成 — 第一阶段

日期：2026-10-31。**状态：只读证据预检实现 / 尚未做 Owner Mac 完整回归与真实端到端验收。**

## 工作结论

- 五个已知参数更新 Job 的当前 12 个 HF Bucket 对象：Owner SAFE 回执对账通过；对应六个冻结 split 为 184 个记录位置，五次 Job 关联为 344 个记录位置（都非独立样本数）。
- G1 固定五个候选世界：一个历史 SFT UUID 排除，剩余四个与已检查 R50 五世界、部分 Gold/DEV/R04 历史集合局部排除；**其他 protected/heldout UUID 全集仍缺失**。
- 历史 69 个可见 HF Job 中 60 个仍未充分分类，历史输入对象不可变性未知。即便五 Job 当前哈希匹配，也不满足 `all_actual_sft_runs_and_input_sources_proven_complete`。
- G2 Prompt 组装：19 个来源组件、17 个字节级阻断；缺目标到 request_id 的直接因果联系和原始 Provider 请求输入。禁止靠时间关联补造 PASS。

## 新增文件

- `docs/evidence/R58_G1_G2_SKILL_V02_READINESS_MATRIX_SAFE_20261031.json`：聚合 G1/G2 证据与缺口，**不包含**故事 UUID/候选原文。
- `skills/storyforge-roleplay-sft/v02/r58_evidence_preflight.py`：只用 `git cat-file blob` 定点读取四个固定 SAFE JSON，校验源约束、状态与门禁，不读取私有材料；缺证据时 exit 42。
- `skills/storyforge-roleplay-sft/v02/test_r58_evidence_preflight.py`：12 个合成测试，包含篡改、漏源、假 PASS、R50 不当访问标记与路径输出防泄漏。
- `skills/storyforge-roleplay-sft/v02/README.md`：限制和执行命令。

## 尚未完成

1. 当前 PR #7 的 GitHub Actions 最新原有 HEAD（`1b9302c26d894fb269bad585368377d01b6a7e0c`）报告 `CI=failure`；本轮无法获取该 Job 的完整日志，**不能宣告测试基线 PASS**。
2. v0.1 `shortlist/gate/freeze` 仍与 v0.2 的权威证据接口分离；v0.1 对候选级 Reviewer/来源主要验证声明，不能自动认定事实已验证。后续应先改成签名/固定证书的候选准入，不从自声明布尔值放行。
3. 无独立 G1 历史来源完整性、G2 原始请求字节证据；G3 双盲审核、Dataset v0.4 冻结及 HF CPU/GPU 尚未授权和启动。

**门禁不变：`G1=HOLD`、`G2=HOLD`、Train/Validation/Teacher `0/0/0`、`expansion_allowed=false`、R50 sealed、PR #7 Draft。**
