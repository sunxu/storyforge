# StoryForge R58 — HF 私人 GPU 批量语义审查（PREPARED，未经付费运行授权）

## 授权边界与目标

Owner 2026-11-01 确认：R58 **132 条 Assistant-first Gold 的私人内容可以在 Hugging Face 私人计算环境**用于语义审核；这与先前对 Grok 网页的授权分开。当前仅授权**设计与本地准备**，不等于立即上传私人文件、启动 HF Job、付费 A100 或训练模型。任何 GPU 推理前还需给出确切 model revision、镜像、Job 命令、超时与最坏费用，再单独获得启动确认。

目标不是 Gold 文学质量打分，而是判断删除历史第一条 Assistant 会否破坏人物/关系、时间线、硬规则、玩家自主，以及能否从后续历史/卡片补足。推理结论只属于 review recommendation，不自动删历史、不授权 Quality-v1；13 份世界卡快照仍未经认证。

## 已提交代码

- `gold195_hf_review_batch.py` — 将冻结的私人 132 条任务变成独立 HF 输入包；本地结果证据核对，打印 SAFE 统计，不联网；
- `gold195_hf_review_gpu_runner.py` — **只有明确给定** `--confirm-paid-gpu` 且在 `--calibration-only` / `--allow-full-run` 中恰选一个才会加载 vLLM GPU。没有内部自动 HF Job 启动 API；
- `test_gold195_hf_review_batch.py` — 合成数据下校验不得泄露真实故事、引用必须是源子串、checkpoint 不覆盖、缺失样本继续 HOLD。

## 第一步：Mac 上创建新的私有 HF 输入（不上传）

在 `sunxu/storyforge` 的 R58 分支根目录执行：

~~~bash
git pull --ff-only
R58_PRIVATE="$HOME/.local/share/storyforge/r58"

python3 -m unittest discover -s experiments/r58_quality \
  -p 'test_gold195_hf_review_batch.py' -v

python3 experiments/r58_quality/gold195_hf_review_batch.py \
  --repo-root "$PWD" \
  --private-comparison-input "$R58_PRIVATE/gold195-assistant-first-comparisons-v1.jsonl" \
  --private-full-tasks "$R58_PRIVATE/gold195-assistant-first-review132-v1.jsonl" \
  --prepare-dir "$R58_PRIVATE/hf-semantic-review132-v1"
~~~

预期 `HF_PRIVATE_INPUT132_PREPARED__NOT_UPLOADED`，并严格要求 `source_rows_verified=132`。新建目录中有 `input132.private.jsonl` 和 `manifest.private.json`（均 0600）。原 Gold、比较包、Grok 审核包、R50 全部保持不变。**不要将此目录上传 GitHub 或本对话**。

上传前应检查整份卡片是否混入秘密、与训练无关的元数据或未来剧情；工具不主动改写快照，因此上传会包含 **完整的故事与世界卡私人内容**。匿名 review_label 只能减少外露真实 case ID，不能使小说正文匿名。

## 预定 HF 存储隔离（尚未执行）

使用现有 private bucket `hf://buckets/adradar/storyforge-training` 中**新建专用子目录**，例如：

- `r58/hf-semantic-review-v1/input/input132.private.jsonl`：来自 Mac 的 132 条审核任务； 
- `r58/hf-semantic-review-v1/input/manifest.private.json`：来源哈希记录；
- `r58/hf-semantic-review-v1/calibration/`：前 10 条的输出；
- `r58/hf-semantic-review-v1/full/`：后续全部 132 条的输出。

不得让 Job 搜索训练目录、R50 目录或其他受保护素材；Job 只能使用精确指定的 `input132.private.jsonl` 路径。HF Job 挂载整个 bucket 仅提供技术访问能力，应用代码必须严格白名单限制读取路径。若需要更强的存储隔离，应采用单独 private bucket 或只挂载受限子目录，待实际 Job 方案确认。

## 运行设计（**不要直接执行，待付费授权**）

建议使用官方兼容 vLLM 的 CUDA 镜像（固定不可变 digest），配置单张 A100 80GB，指定经过验证的 `Qwen/Qwen3-32B` 40 字符完整 commit revision，HF Jobs `timeout` 设为硬截止，并在代码内部设置 `--max-wall-seconds`。模型实际能否在 80GB BF16、KV cache 以及 8192 上下文窗口内加载，尚未经真实 GPU 验证。存在 OOM 可能，不能将“推荐 A100”当作性能保证。

首次 **10 条校准**，使用 `--calibration-only --confirm-paid-gpu`；只有真实质量校准完成，再另行批准 `--allow-full-run --confirm-paid-gpu` 处理 132 条。即使已提供 HF 数据上传授权，仍不等于批准以上参数。所有 Job 命令、挂载、费用和镜像需在提交前再次检查。模型调用仅接受 pinned revision；每条完成后以 `full001.json` 等写入私人目标目录，带 source-row SHA256、固定模型 revision，已存在的不同来源/model 立即 HOLD；不把私人正文写入日志。无法符合 token 限制的样本不偷偷截断，而计作 token_hold。

最坏费用保护必须是**平台 Job timeout 与代码 wall-time 双层**；不能只依赖推理脚本限时，因为模型加载过程也消耗付费 GPU 时间。若用示例单价 ¥18/小时预算，2 小时仅是约 ¥36 的算力估算，尚不含其他收费与汇率波动；只有确定 HF 当前价格、实际超时和运行方式后才能给明确预算。

## Mac 上验证已返回的私有结果（不调用云端）

校准阶段先仅验证前 10 条：

~~~bash
python3 experiments/r58_quality/gold195_hf_review_batch.py \
  --repo-root "$PWD" \
  --private-input-jsonl "$R58_PRIVATE/hf-semantic-review132-v1/input132.private.jsonl" \
  --audit-results-dir "$R58_PRIVATE/hf-semantic-review132-calibration-v1" \
  --calibration-only
~~~

运行全量后，去掉 `--calibration-only` 并换成完整结果目录。回执会统计 `MISSING_RESPONSE`、`EVIDENCE_QUOTE_INVALID`、`PROVISIONAL_DROP_NOT_APPROVED`、`PRESERVE_RECOMMENDATION`、`SEMANTIC_HOLD`。形式完整 ≠ 独立文学或事实判断准确。严重争议个案仍需人工或不同模型复核，不因单一 Qwen 输出直接批准截断。

本阶段不创建训练集、不会读取 R50、不会自动启动 HF Jobs、不会自动向 HF Bucket 上传任何私人原文。
