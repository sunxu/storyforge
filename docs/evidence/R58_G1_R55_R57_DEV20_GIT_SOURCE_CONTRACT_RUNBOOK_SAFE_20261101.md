# R58 G1 — R55 / R57 已知 DEV20 来源代码合约核验（SAFE）

日期：2026-11-01。分支 `r58/roleplay-sft-skill-v01`，Draft PR #7。**不触碰 PRIVATE 候选或保护正文**。

## 为什么这次有意义

此前 22 个 PRIVATE 文件名候选已完成发现，但其 29 条范围关联都不能仅凭名称成为可信索引。GitHub 现有版本化代码可以验证**部分旧开发来源的固定生成链**：

- R48 原始 Test 校验器 `scripts/v02_r48_four_arm_build.py` 定义旧 v0.1 Test 的 SHA256；R55 `scripts/v03_r55_gold5_build.py` 的 `load_exact_sources()` 校验原 Test、冻结提示 Git Blob 和 manifest，要求 20 题、20 Gold、20 份各模型回复。
- R55 v2 `scripts/v03_r55_gold5_review_v2.py` 仍调用原 R55 的 `legacy.load_exact_sources()`，因此 v2 不是独立新世界的来源生成器。
- R55 `configs/v03_r55_exposed20_pairwise_dev_contract.json` 声明 R47/R48 重用同 20 个开发题、2 个旧世界、非独立 Held-out。
- `docs/evidence/R57_BPROMPT_DEV20_FINAL_SAFE_20261028.json` 的 Owner SAFE 报告声明 BPrompt 也是 2 世界/20 对旧 DEV，用相同模型权重做 Prompt 对比；10 个严重问题候选是其报告范围内的子集（40 verdict slots）。**但该 SAFE 报告没有提供原始私人逐题输入映射的独立回放**。

本次只检验这些 Git 固定代码和 SAFE JSON 是否符合既有明确合约，不打开旧 v0.1 Test 源字节，不读取 Prompt/回复、R50、R57 PRIVATE 映射、HF 目录、Job 日志，也不运行模型或写任何文件。Git Blob SHA pin 是固定代码/回执身份，不是对真实 Provider 历史数据消费的证明。

## 执行

在已配置上游的 R58 工作区运行：

```bash
git pull --ff-only
python3 -m unittest discover -s experiments/r58_round1 \
  -p 'test_r58_g1_r55_r57_dev20_source_contract_audit_safe_20261101.py' -v
python3 experiments/r58_round1/r58_g1_r55_r57_dev20_source_contract_audit_safe_20261101.py \
  --repo-root "$PWD"
```

只发给我 9 个纯合成测试的简短 PASS/FAIL 摘要和第二条工具的 **SAFE JSON**。若 Git 对象缺失、源码契约改变、回执字段不符，程序固定输出 HOLD、退出码 42；不上传 Python traceback、任何 PRIVATE UUID 或来源正文。此脚本未在 Owner Mac 上真实运行；在 Owner 回传之前不能记 E2E PASS。

## 核验通过的边界

仅可把 R55 Gold5 v1/v2 的固定**旧 DEV20 来源构建合约**，和 R57 BPrompt 的 **Owner 声明的 DEV20/DEV10 范围**列为同一历史复用方向的证据。严禁将其解释为：R57 私人逐题来源已被独立复核、整个 R55/R57 开发/仲裁世界全集已封闭、所有 Reserved/Heldout 世界已封闭，或其他 60 个 HF Job 的参数更新和输入来源已清楚。

在没有新的权威来源注册表时，**不要继续增加文件名索引扫描器**；也不要为补足缺口打开 R50 密封题或历史原始故事。

**门禁不变：** G1=HOLD、G2=HOLD、G3=NOT_STARTED、Train/Validation/Teacher=0、`expansion_allowed=false`；五个固定原候选中一项已排除，其他四项仍 HOLD；不自动扩样或训练。

