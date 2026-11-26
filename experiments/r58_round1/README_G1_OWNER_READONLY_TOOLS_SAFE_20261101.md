# StoryForge R58 G1 — Owner 已用只读取证脚本归档（SAFE）

日期：2026-11-01。仅适用于 `r58/roleplay-sft-skill-v01` / Draft PR #7。

## 归档意图与版本

本目录下四份脚本最初在 Owner Mac 上按限域授权执行；现将**当时使用的脚本原文**归档以便审计与复现。不是扩权、升级 G1 或补造历史 Trainer 工件。后续修改须使用新提交并保持审计链。

| 脚本 | 用途 | 归档文件 SHA256（本次静态核验） |
|---|---|---|
| `r58_g1_one_job_trainer_artifact_probe_safe.py` | 已固定 CANCELED Job 的 Trainer state / Checkpoint 存在性诊断 | `6a597a26efc17fabbe37f84ad071450733d1efe7c2c000e5933cfe25f65a8c93` |
| `r58_g1_priority_bucket_input_sha256_readonly.py` | 单 Job 现存 Train/Validation 字节流 SHA256，私人 0600 回执 | `433d0b4e3907acbcf22fc32889804cadc919c32ccc5332509dc613d04d53bf62` |
| `r58_g1_priority_tensorboard_scalar_readonly_20261101.py` | 单 Job 既存 TensorBoard TFRecord CRC32C / 允许标量核验 | `2f3f40c2c1c09f1b5ab992769ac807c5f8005a71029fe5bfbe73341f9f32dd9b` |
| `r58_g1_other_three_jobs_private_ledger_crosscheck_safe.py` | 额外三目录与既存 60 项 PRIVATE 未分类 Job 账本精确关联 | `a5b9f984b48cb2d10ba4dda3836e27c3214119c6cd95bf72dbc74014743d015b` |

以上为脚本自身哈希，并非训练样本或私有 Job 的哈希。不能将它们等同于历史远端证据强度。

## 本轮核验与结果

- 保存前核对过四份原文的 Python AST 语法、禁止硬编码私有 Job ID / 明显密钥的静态检查。
- 以**人工构造数据**验证过 SHA256 流式处理、CRC32C / TFRecord 最小记录、60 项 PRIVATE 清单集合关联的逻辑；这些不是新的 HF Job 运行。
- 未在此归档流程进行完整项目单元测试、Ruff 或全部 HF 实测；不可据此写出整体 PASS。
- Owner Mac 回传的新 SAFE 回执：`docs/evidence/R58_G1_OTHER_THREE_GPU_PRIVATE_LEDGER_MATCH_SAFE_20261101.json`，属 **OWNER_MAC_REPORTED**，额外 3/3 确认在原 60 项 PENDING 中；本轮未独立读取 Owner 本机 PRIVATE 账本。
- 原始直接目录发现：`docs/evidence/R58_G1_OTHER_GPU_JOB_BUCKET_METADATA_TRIAGE_SAFE_20261101.json`；目标 CANCELED Job 的日志 / TensorBoard 交叉证据：`docs/evidence/R58_G1_CANCELED_GPU_TENSORBOARD_SCALAR_CROSSLINK_SAFE_20261101.json`。

## 运行边界与本地拉取

所有脚本只在明确的 Owner 授权和匹配的 Git 分支/既存私人账本范围内运行。默认不会提交或启动新 HF Job，不读原始训练正文，不输出 PRIVATE Job ID，也不会放开 G1。

```bash
cd ~/workspace/storyforge-r58-run
git switch r58/roleplay-sft-skill-v01
git pull --ff-only origin r58/roleplay-sft-skill-v01
python3 -m py_compile experiments/r58_round1/r58_g1_*.py
```

以上只是**拉取与本地语法检查**，不访问 HF、不产生新的 SAFE 取证结论。历史执行回执已经存在时，**无需重复运行取证脚本**。特别是输入 SHA256 脚本采用独占新建的私人输出文件（`O_EXCL`），重复执行到同一输出路径会故意返回 HOLD，不应删除或覆盖旧回执来绕过保护。

如需未来重核，必须明确目标、范围、输出位置及单独授权，先将经过审阅的代码提交 GitHub，再由 Owner 拉取并执行。

## 不变门禁

`G1=HOLD`、`G2=HOLD`、`G3=NOT_STARTED`、`Train/Validation/Teacher=0`、`expansion_allowed=false`，不自动扩样、GPU SFT、合并 main 或晋升。
