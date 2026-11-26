# R58 — HF CPU132 Tokenizer：沿用 StoryForge sync → submit → verify

## 项目已有 HF 规范（2026-11-01 核查）

- [docs/HF_JOBS.md](../../docs/HF_JOBS.md)：`adradar`、Bucket、付费提交前必须明确审批；
- [docs/V03_R53_HF_CPU40_SUBMIT_VERIFY_CN.md](../../docs/V03_R53_HF_CPU40_SUBMIT_VERIFY_CN.md)：`cpu-upgrade`、SHA256 检查、Mac 端仅需 hf CLI、结果回收；
- [docs/README_R50_HF_CPU46_SYNC_SUBMIT_VERIFY_CN.md](../../docs/README_R50_HF_CPU46_SYNC_SUBMIT_VERIFY_CN.md)：严格隔离 R50、独立 RUN_KEY、远端文件逐一回读；
- [docs/evidence/V03_R50_CPU46_TOKENIZER_REVISION_PATH_ROOT_CAUSE_FIX_20261022.md](../../docs/evidence/V03_R50_CPU46_TOKENIZER_REVISION_PATH_ROOT_CAUSE_FIX_20261022.md)：历史 tokenizer revision 快照路径错误，不允许用未固定版本的缓存代表测试成功。

R58 的目标数据已有 Owner SAFE `HF_PRIVATE_INPUT132_PREPARED__NOT_UPLOADED`，132/132。**不要在 Mac 运行 Transformers tokenizer**，Mac 只负责标准库校验、Bucket 同步和回收验收。

## 已新增代码

- `gold195_hf_review_cpu_worker.py`：HF CPU Worker，本地 staged 文件逐个 SHA256，固定 Qwen3-32B revision，统计真实 `prompt_tokens`，不上载模型权重、无推理；
- `gold195_hf_review_cpu_stage.py`：Mac 标准库生成只读代码与私人输入的哈希固定 stage；
- `hf_cpu132.sh`：`sync`、`submit` 和 `verify` 分离，实际计算**只有 submit**；
- `test_gold195_hf_review_cpu_worker.py`：合成 Stage、哈希修改 HOLD、132 条数量与上下文长度逻辑测试。

## 1. Mac 同步（需要已有 hf CLI 和凭据；不启动计算）

~~~bash
git switch r58/roleplay-sft-skill-v01
git pull --ff-only
hf auth whoami
python3 -m unittest discover -s experiments/r58_quality -p 'test_gold195_hf_review_cpu_worker.py' -v

bash experiments/r58_quality/hf_cpu132.sh sync
~~~

仅将 Mac 已准备的 `input132.private.jsonl`、固定 Worker 和 GPU 侧同源 prompt 渲染模块同步到 `hf://buckets/adradar/storyforge-training/preflight/r58/hf-cpu132/runs/<RUN_KEY>/`，不会读取或上传 R50。**该 Bucket 必须实际确认 `private=true`**；组织其他获授权人员仍可能看到私有正文。若要求硬隔离，应先迁移到独立的私有审核 Bucket。

Stage 文件权限 0600、stage 目录 0700；每次 sync 使用新的 `RUN_KEY`；提交 Job 前对四份远端文件逐一下载比对。回执 `R58_HF_CPU132_REMOTE_STAGE_BYTES_PASS__NO_JOB` 不代表实际 tokenizer 已执行。同步也可能产生网络和存储成本，但不创建 CPU/GPU Job。

## 2. 付费 CPU 提交（当前未授权，请勿自行执行）

**只有 Owner 单独确认具体一次收费 CPU Job 之后**，才允许以下命令；此处仅说明预定合同，不是授权：

~~~bash
RUN_KEY='替换为 sync 实际输出'
STORYFORGE_ALLOW_PAID_CPU=YES STORYFORGE_R58_CPU132_NO_GPU=YES \
  bash experiments/r58_quality/hf_cpu132.sh submit "$RUN_KEY"
~~~

固定 `--namespace adradar --flavor cpu-upgrade --timeout 90m`，`python:3.12-slim`，`CUDA_VISIBLE_DEVICES=""`，`transformers==5.16.1`；只下载 tokenizer，不加载完整 Qwen3-32B 权重、不做模型生成、HF GPU 不用。平台 90m 为硬上限，不是预计耗时。**同一 RUN_KEY 只允许提交尝试一次**；CLI 超时或无法确定是否创建 Job 时先查询 `hf jobs ls -a --namespace adradar`，不能重复提交。

## 3. 回收验证（仅在实际远端完成后）

~~~bash
RUN_KEY='sync 实际输出'
bash experiments/r58_quality/hf_cpu132.sh verify "$RUN_KEY"
~~~

只获取 `R58_HF_CPU132_SAFE.json`：132 条总数、fits_context、token_hold、min/median/P95/max、模型 revision；不输出故事正文、身份或单条 token 长度。该报告是运行时统计，不会批准截断、训练或世界卡。

## 进度与 HOLD

- 已确认：本地 HF 私人审核输入 132 条已准备；R50 封存；Quality-v1=0。
- 未确认：R58 HF 远端 stage 同步、真实 CPU Job、132 条 tokenizer 统计、模型 GPU 适配。
- 默认保留 GPU 未授权与付费 CPU 未授权；现有代码需要 CI 及 Mac 端实际验证，未声称 remote PASS。
- 与历史 R50 修复不同，R58 新 Worker 使用公开 HF revision 字符串通过 `AutoTokenizer.from_pretrained(..., revision=固定 SHA)` 加载；不复用 R50 受限原始 preflight，也不把 R50 任务复制到训练 Bucket。
