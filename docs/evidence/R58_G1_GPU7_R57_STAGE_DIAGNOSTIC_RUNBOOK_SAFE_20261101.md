# StoryForge R58 — GPU7 / R57 / 冻结 Git 文档核验失败阶段诊断（SAFE）

日期：2026-11-01，Draft PR #7，仅 `r58/roleplay-sft-skill-v01`。

## 已发生的 HOLD

Owner Mac 运行 `r58_g1_gpu7_r57_and_git_doc_links_readonly_20261101.py` 后返回 `GPU7_R57_OR_FROZEN_DOC_METADATA_UNAVAILABLE__G1_HOLD`，没有给出失败阶段。该结果已经作为 Owner SAFE 回执保存：`docs/evidence/R58_G1_GPU7_R57_GIT_DOC_OWNER_HOLD_RECEIPT_SAFE_20261101.json`。

原因**尚未证实**；不能在没有具体证据时认定是 PRIVATE 账本、R57 目录、集合不一致或 Git 扫描中的某一个。

## 限域诊断

运行已先行提交 GitHub 的 `experiments/r58_round1/r58_g1_gpu7_r57_stage_diagnostic_safe_20261101.py`。代码复用原核验模块，只读检查 4 份既存 PRIVATE 账本、单个 `evaluation-runs/v03-r57` 目录名称，以及 HEAD 下已受控 `.md/.json` 冻结文档引用。先检查 Git 文档，再访问 HF 目录，以避免本地证据异常时不必要的远端读取。

失败只返回固定 `failed_stage` 枚举和必要的聚合计数；不会返回原始异常、Job ID、PRIVATE 路径、文档内容或训练数据。没有修改或新建 PRIVATE 文件，不启动任何 HF Job。

## Owner Mac：先 Pull，再执行

```bash
cd ~/workspace/storyforge-r58-run
git status --short
git switch r58/roleplay-sft-skill-v01
git pull --ff-only origin r58/roleplay-sft-skill-v01
python3 -m py_compile experiments/r58_round1/r58_g1_gpu7_r57_stage_diagnostic_safe_20261101.py
python3 experiments/r58_round1/r58_g1_gpu7_r57_stage_diagnostic_safe_20261101.py --repo-root "$PWD"
```

只返回 stdout SAFE JSON 与退出码，**不要分享 PRIVATE 账本、Job ID 或 Python traceback**。诊断可能因依赖、凭证或远端元数据原因 HOLD；每一个 HOLD 都继续禁止扩样，不应该绕过校验或扩大读取范围。

## 停止规则与边界

只有获得明确的 `failed_stage` 后，才决定是否进行最小修复。如果阶段是 `R57_EXACT_JOB_SET_BINDING`，可使用该 SAFE 聚合计数判断 4 个目录匹配是否实为不同 Job，但仍不读取日志或推断训练用途。即使全部检查通过，仍只证明路径与文档引用，不能解除 G1。

本次仅进行静态范围核查和 GitHub 内容回读。**尚未进行 Owner Mac 端到端执行、完整 Ruff 或 unittest**。G1=HOLD、G2=HOLD、G3=NOT_STARTED、Train/Validation/Teacher=0、`expansion_allowed=false`。
