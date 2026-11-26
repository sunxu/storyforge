# R58 G1 — 18 个待分类 GPU Job 的 Bucket 目录覆盖核验（SAFE）

日期：2026-11-01。分支：`r58/roleplay-sft-skill-v01`；仅在 Draft PR #7 上操作。

## 源码与已知边界

工具：`experiments/r58_round1/r58_g1_gpu18_bucket_metadata_coverage_readonly_20261101.py`。

- 原始 Owner PRIVATE 账本：60 个 Job，GPU 18 / CPU 42；不重建、覆盖或升级任何现有分类。
- 前期已验证 3 个额外 GPU Job 与原有账本 3/3 匹配，优先 CANCELED Job 也在 60 项账本内；因此此前观察的两个根目录中应有原始 GPU18 的 4 个 Job 专属目录。这是**既有证据预期**，仍需 Owner Mac 本轮实际 SAFE 回执核对。
- 只读取 `hf://buckets/adradar/storyforge-training/runs` 和 `.../baseline-runs/capacity` 两处的**直接子目录名称**；不声称其他 Bucket 根目录、外部输出、已删除任务和其他平台不存在。
- 复用已归档的 PRIVATE 账本安全读取器与 9 个已知 Job 身份注册表；逐 Job 对应关系仅进入新建的 0600 PRIVATE 回执，终端仅输出聚合。
- 不调用 `HfApi.run_job`，不启动 GPU/CPU；不读取 Job command/args、日志、原始训练数据、R50/DEV 内容；不能证明 optimizer step、参数更新或历史输入实际消费。
- 未见 Job 目录只能标为**当前扫描根路径没有同名目录**，绝对不能当作无训练证明。

## 本地执行（请先 Pull）

依赖：当前已验证可访问 HF Bucket 的 Owner Mac 环境、已存在的原始 60 项 PRIVATE 未分类 Job 账本与 CANCELED 优先账本；PRIVATE 账本权限为 0600，输出目录不能允许其他用户访问。

```bash
cd ~/workspace/storyforge-r58-run
git status --short
git switch r58/roleplay-sft-skill-v01
git pull --ff-only origin r58/roleplay-sft-skill-v01
python3 experiments/r58_round1/r58_g1_gpu18_bucket_metadata_coverage_readonly_20261101.py \
  --repo-root "$PWD"
```

仅将终端的 SAFE JSON 返回聊天。新 PRIVATE 回执存于：

`~/.storyforge-r58-private/round1_pilot_20261030/g1_gpu18_bucket_prefix_metadata_PRIVATE_20261101.json`

该文件由既有安全写入器独占创建；如果路径已经存在，脚本故意 HOLD，不要删除或覆盖旧证据，也不要上传 PRIVATE 账本、Job ID 或原始文件。

## 代码检查与门禁

提交前在隔离环境完成 Python AST、`py_compile` 和人工合成 60 项账本的 18-GPU 集合、错分类拒绝、缺失优先任务拒绝的离线检查；**不是 Owner Mac HF 端到端测试，不代表 Ruff 或完整项目测试通过**。

结果仍必须是：`G1=HOLD`、`G2=HOLD`、`G3=NOT_STARTED`、`Train/Validation/Teacher=0`、`expansion_allowed=false`。后续是否对某一新高风险 Job 的原始日志或训练输入取证，需要单独明确授权。
