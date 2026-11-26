# StoryForge R58 G1 — GPU7 R57 路径与冻结 Git 文档引用交叉核验（SAFE）

日期：2026-11-01。仅适用于 `r58/roleplay-sft-skill-v01` Draft PR #7。

## 已冻结事实

- Owner Mac 已核实：7 个 COMPLETED GPU Job 中，4 个只在 `evaluation-runs` 出现路径名称引用，3 个在五处检查根目录中仍无引用。
- 本轮 Owner SAFE 回执：`docs/evidence/R58_G1_COMPLETED_GPU7_OTHER_ROOTS_OWNER_RECEIPT_SAFE_20261101.json`；原始 18 个 GPU 与 42 个 CPU Job 全部继续 PENDING。
- 此前 HF Bucket 只读元数据扫描在 `evaluation-runs/v03-r57` 观察到 12 个文件、4 个格式符合 Job ID 的路径 token，没有同目录下命名为 `trainer_state.json`、`optimizer.pt` 或 `.safetensors` 的文件。**这未与 PRIVATE 7 个 Job 精确关联，也不能证明从未更新权重。**

## 本次脚本

路径：`experiments/r58_round1/r58_g1_gpu7_r57_and_git_doc_links_readonly_20261101.py`。

脚本只读取已有的 60-Job、优先 CANCELED、GPU18 目录、GPU7 五路径 PRIVATE 元数据回执；仅枚举指定 `evaluation-runs/v03-r57` 目录及其子目录名称；复用 `check_hf_job_documentation_coverage.frozen_job_mentions` 从受控 Git HEAD `.md/.json` 文档提取 Job-ID 引用集合，输出 4/3 两组文档关联计数。

不能凭 `evaluation` 路径或 Git 文档引用判断 Job 仅评估，不能由缺少 Trainer state/optimizer 文件断言无优化器更新。不读取 HF Job 日志、命令、参数、训练集或 R50 密封内容；不创建和不覆盖任何 PRIVATE 文件；不启动 HF Job。

## Owner Mac：先 Pull 再执行

```bash
cd ~/workspace/storyforge-r58-run
git status --short
git switch r58/roleplay-sft-skill-v01
git pull --ff-only origin r58/roleplay-sft-skill-v01

python3 -m py_compile experiments/r58_round1/r58_g1_gpu7_r57_and_git_doc_links_readonly_20261101.py
python3 experiments/r58_round1/r58_g1_gpu7_r57_and_git_doc_links_readonly_20261101.py --repo-root "$PWD"
```

只回传 stdout SAFE JSON；失败则只报告 SAFE HOLD 与退出码，不分享 PRIVATE ID 或原始异常。此脚本未在 Owner Mac 上做真实端到端测试；不得宣称完整 Ruff 或 unittest PASS。

**停止规则：**本轮后若仅有目录名或文档引用，不再重复名称扫描。需要原始 Job 角色及 Trainer 更新 / 历史输入消费证明，或保持 HOLD。G1/G2 HOLD、G3 NOT_STARTED、Train/Validation/Teacher=0、禁止扩样。
