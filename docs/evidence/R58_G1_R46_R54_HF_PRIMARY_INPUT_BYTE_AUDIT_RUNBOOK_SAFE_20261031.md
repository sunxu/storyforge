# StoryForge R58 G1 — R46/R54 既有远端训练输入只读哈希核验（SAFE）

2026-10-31。当前已知历史 6 份 split 共 184 条记录位置；Owner Mac 299 项测试及 11 个 Git 证据对象校验通过。此前仍缺失本轮对 HF 原始 Trainer 输入字节的重新核对。**这一步只处理 R46、R54 四个预先固定的原始运行目录文件，不处理未知 60 个 Job，也不启动 HF 任务。**

## 范围、来源、保密

- R46：原始运行目录 `experiments/v02-r46/r46-20261014T070529Z-248172/{train,validation}.jsonl`。`scripts/v02_r46_gpu_runner.py` 明确将同目录中的编译输出交给 `swift sft`。核验 Train49 / Validation15，SHA256 取自冻结 R46 原始编译报告及 Owner 远端核验回执。
- R54：正式执行运行 `r54-v2-20261021T161818Z-507469` 的上传 Stage：`preflight/v03-r54/gpu/runs/<run_key>/private/release/{train,validation}.jsonl`。`scripts/v03_r54_gpu_submit.sh` 创建该路径；`scripts/v03_r54_gpu_runner.py` 读取该 Stage 并在训练前逐字节校验。核验 Train31 / Validation9，SHA256 取自冻结 R53 私有发布记录与 R54 runner 的 EXPECTED 字面量。
- **只读流式哈希：** 通过 `HfFileSystem.open(..., "rb")` 对既有四个文件计算 SHA256 和行数；内存缓冲最多 1 MiB，一文件超过 6 MB 即 HOLD。不保存本地临时正文、不解析 JSON、不打印文件内容、HF URI、任务 ID、密钥或异常原文。
- **默认不允许读取：** 只有 Owner 显式附加 `--allow-read-only-private-primary-input-bytes` 才访问私有 HF Bucket。命令不调用 `hf jobs run`、不调用 GPU、CPU Job，不写任何 Bucket 文件。
- 本轮对“当前 Bucket 对象的字节等于 Git 冻结契约”的检验 **不等于证明历史运行期间对象不可变或完整历史 Job 清单**。即使全部通过，G1 继续 HOLD。工具不检查 R50 正文，也不承诺远端四文件绝对不包含 R50；如不愿读取任何可能涉及 R50 的训练文件，就不要执行可选核验。
- `read_only_primary_input` 需要 Mac 登录有权读取 `adradar` 私有 Bucket 的 HF 账号；若文件不存在、权限不足或哈希不一致，一律安全终止且无原始信息输出。

## Owner Mac 运行

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
python3 -m unittest discover -s experiments/r58_round1 -p 'test_*.py' -q

# 明确允许从四份固定的现有私有 Bucket 文件读取字节，仅用于 SHA256；不保存训练文本。
python3 experiments/r58_round1/check_hf_primary_input_bytes.py \
  --allow-read-only-private-primary-input-bytes
```

只回传最后一步的 SAFE JSON 或通用 HOLD 错误，不回传私有 Bucket 文件、终端凭据、源故事 UUID、原始训练文本。

## 可接受结论

若四份文件和行数都与 Git 冻结哈希一致，只能确认 **R46/R54 当前原始运行路径的文件字节符合冻结契约**。`current_bucket_equality_proves_historical_job_read_these_bytes=false`、`source_registry_complete=false`、`all_actual_sft_runs_and_input_sources_proven_complete=false`。v0.1 Smoke / Capacity / Baseline 的原始输入任务归属、其他未分类历史任务及所有受保护来源，仍是独立缺口。

`G1=HOLD`，Train/Validation/Teacher 准入 0，`expansion_allowed=false`，PR #7 仍保持 Draft；不授权新的 HF Job。
