# StoryForge HF Jobs 实战手册：Mac CLI、Bucket、CPU Tokenizer/Collator（2026-11-12）

> 证据等级：以下「已验证」基于 Owner Mac SAFE 回执和 HF Job inspect/日志；「限制/待核」不得误写为 PASS。本手册记录 R60 Common2 实际成功路径，其他模型或 GPU Job 不得机械套用。公共安全规范仍以 `docs/standards/HF_JOBS_ENGINEERING.md`、`skills/storyforge-hf-jobs/SKILL.md`、`scripts/hf_job_guard.py` 为准。

## 1. 已成功运行的环境与角色边界

| 项目 | 成功配置或边界 |
|---|---|
| 代码仓库/隔离分支 | `sunxu/storyforge` / `r60/common2-cpu2-owner`；Owner Mac 工作树 `~/workspace/storyforge-r60-4router-review` |
| OS/工具角色 | macOS Apple Silicon M4 Max：仅打包、Git、合成 pytest、HF CLI/SDK、只读验收；**不要求本机安装 Swift/PyTorch** |
| HF CLI | Homebrew `/opt/homebrew/bin/hf`，Owner 已验证版本 `hf --version = 2.4.0` |
| HF SDK Python | `$HOME/.local/share/storyforge/venvs/hf-cli/bin/python`；已见 `huggingface_hub==1.6.0` 的 SDK API 限制；**不能假定此版本与 CLI 2.4.0相同** |
| 本地 pytest Python | `$HOME/.local/share/storyforge/venvs/r60-tests/bin/python`；轻量环境可能没有 `httpx`、Torch、Swift |
| HF 组织 | `adradar`；Bucket `hf://buckets/adradar/storyforge-training` |
| CPU flavor | `cpu-upgrade`（私有 Collator 正式检验）；公开合成诊断使用 `cpu-basic` |
| Job image | `pytorch/pytorch@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee`，固定 **manifest digest**，不是浮动 tag/config digest |
| Job Python | 镜像日志显示 `/opt/conda/lib/python3.11`；Linux x86_64，CPU-only |
| 超时与重试 | 120 min、`--attempts 1`、`--detach`；每 RUN_KEY 最多一次正式提交，无隐式重试 |
| 名称与环境变量 | `--namespace adradar`、`--name r60-cpu2-<RUN_KEY>`、`--env STORYFORGE_R60_COMMON2_RUN_KEY=<RUN_KEY>` |
| 输入 mount | `hf://buckets/adradar/storyforge-training/preflight/r60/common2/cpu2/runs/<RUN_KEY>:/input/common2:ro` |
| 输出 mount | `hf://buckets/adradar/storyforge-training/preflight/r60/common2/cpu2/results/<RUN_KEY>:/output:rw` |
| 执行指令 | `bash /input/common2/code/scripts/r60_common2_hf_cpu_worker_v2.sh`；镜像后无需额外 `--` |
| SAFE 结果 | `/output/R60_COMMON2_CPU2_SAFE_RECEIPT.json`，O_EXCL、0600，最大8192字节；用户私有结果不进入 GitHub |
| CUDA/本体约束 | `CUDA_VISIBLE_DEVICES=""`、`USE_HF=true`、`TOKENIZERS_PARALLELISM=false`；不加载模型权重/不推理/不训练 |

固定模型：`Qwen/Qwen3.8-27B`，revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`（40位），Tokenizer+配置文件，不下载27B权重。HF容器安装实际版本：`ms-swift==4.5.3`、`transformers==5.16.1`、`tokenizers==0.23.3`、`huggingface_hub==1.33.0`、`qwen-vl-utils==0.0.14`、`decord==0.6.0`、`torchvision==0.21.0`，镜像 Torch 2.6.0；**Mac SDK环境与容器 SDK1.33.0是不同作用域，不可混淆**。工作镜像完整依赖的传递版本见对应成功Job日志；不要把未锁定的间接依赖声称为可复现lock。

## 2. SDK 与 CLI 的已踩坑结论

- **旧SDK无法直接提交挂载**：Mac `huggingface_hub==1.6.0` 的 `HfApi.run_job` 不接受 `volumes`、`name`；`inspect_job` 需要 `job_id=` keyword。不要借 SDK 拼原始挂载或降级整Bucket RW。
- **镜像参数位置**：HF CLI版本和 `hf jobs run --help` 需实时固定；旧语法把 `--name` 当镜像，出现 `docker.io/--name`；成功路径使用 `scripts/hf_job_guard.py` 构建+业务 `r60_common2_hf_cpu_cli_dry_run.py` 的适配，不手写猜测参数。
- **插件和 Mac 身份可能不同**：ChatGPT HF插件对私有Bucket RW曾403，Owner Mac CLI可用。插件 `whoami`成功并不能证明 Owner Mac SDK；也不允许因此自动改 Namespace/Token/ACL。
- **SDK/网络**：`list_bucket_tree` 会因HTTP429/5xx、httpx超时、连接异常、401/403/404等返回不同SAFE门禁。兜底 `REMOTE_SDK_OR_SERVICE_HOLD` 不是HF宕机的证明。失败先只读重试同 RUN_KEY 的EMPTY或READY检查，不自动重复上传。
- **分页排重**：`HfApi.list_jobs(namespace=...)` 默认仅100条，不能凭第一页确认不存在；最终验证器分页遍历完整历史（本轮曾见232条）、同时核对输出EMPTY和本地提交标记ABSENT。
- **提交幂等性**：`r60_common2_hf_cpu_cli_submit_once.py` 在真正调用 CLI 前用 `O_EXCL` 创建 `<RUN_KEY>.cpu-submit-v2-attempted`；失败/超时或返回不明确后必须保留marker，不能直接重试同KEY。
- **Bucket部分上传**：manifest最后上传；若中途停止，必须只读核查对象集合，禁止反复 `sync-existing` 覆盖部分内容。全新Stage必须从原始冻结输入派生，独立12位随机尾码和UTC时间，旧Stage字节不动。

## 3. 成功操作顺序及命令（先只读、提交仅显式授权路径）

环境预检：

```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git status --short
export PATH="/opt/homebrew/bin:$PATH"
export R60_HF_SDK_PYTHON="$HOME/.local/share/storyforge/venvs/hf-cli/bin/python"
TEST_PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
test "$(command -v hf)" = "/opt/homebrew/bin/hf"
test "$(hf --version)" = "2.4.0"
"$R60_HF_SDK_PYTHON" -c "import huggingface_hub, httpx"
"$TEST_PY" -m pytest -q tests/test_r60_common2_cpu_batch_shape.py tests/test_r60_common2_cpu_template_phase_safety.py
```

新运行键仅在业务确实需要新验证且所有旧运行状态已归档时，才运行 `bash scripts/r60_common2_cpu2_prepare_next.sh`。它从**原始冻结**Stage生成新的不可变27文件Stage、SHA校验、远端EMPTY、`sync-existing`、CLI Dry-run、完整Job排重，预期 `R60_COMMON2_NEXT_STAGE_READY_PASS__NO_JOB`，**不会提交Job**。若脚本在生成后/上传前HOLD，保持那个Stage；可以直接运行 `r60_common2_hf_cpu_bucket_guard.py empty RUN_KEY --stage STAGE` 并继续同Stage，无需重复创建。

已准备Stage的只读验证（替换为真实已经检查的KEY和STAGE，禁止混用）：

```bash
KEY="r60-common2-cpu2-<UTCSTAMP>-<12hex>"
STAGE="$HOME/.local/share/storyforge/r60/hf-cpu2-stages/$KEY"
"$R60_HF_SDK_PYTHON" scripts/r60_common2_hf_cpu_bucket_guard.py ready "$KEY" --stage "$STAGE"
"$R60_HF_SDK_PYTHON" scripts/r60_common2_hf_cpu_cli_dry_run.py --run-key "$KEY" --stage "$STAGE" --dry-run
"$R60_HF_SDK_PYTHON" scripts/r60_common2_hf_cpu_final_read_only.py --run-key "$KEY" --stage "$STAGE"
```

只有 `CPU2_HISTORY_PAGINATED_PASS__NO_JOB` 且EMPTY输出/无Job/marker absent时，才由Owner**单次**正式调用：

```bash
"$R60_HF_SDK_PYTHON" scripts/r60_common2_hf_cpu_cli_submit_once.py \
  --run-key "$KEY" --stage "$STAGE" --execute
```

**历史成功RUN_KEY不得再次执行以上命令**。成功提交JSON为`CPU2_JOB_SUBMITTED__TRAIN_HOLD`；远端必须再以Job ID inspect最终`COMPLETED`并检查原子的SAFE receipt，**仅Job完成不足以证明业务PASS**。

## 4. 镜像依赖、Qwen3.8/ms-swift 的可重现修复

1. 原始 `decord==0.6.0` 在此镜像会使`pip check`报告精确文本`decord 0.6.0 is not supported on this platform`，实际Python import/cpu(0)可用。Worker只允许**这一个完全匹配**的异常行，任何别的pip报错一律HOLD；不应整体忽略pip check。
2. `transformers==5.16.1` 的 Qwen3.8 `apply_chat_template` 返回`BatchEncoding`，要读`input_ids`并严格验证一维整数数组，不能把BatchEncoding长度2当token数。
3. `swift.get_processor(str(snapshot))` 会因为`model_type=qwen3_5`多候选匹配而ValueError；显式`get_processor(str(snapshot), model_type="qwen3_5")`。
4. `get_template(processor)`因`qwen3_5`与`qwen3_8`两个候选而失败；显式`get_template(processor, template_type="qwen3_8",loss_scale="last_round",max_length=16384,add_non_thinking_prefix=False)`，`set_mode("train")`只用于构造监督标签，不代表启动训练。
5. Qwen3.8的`template.data_collator`计算RoPE时默认尝试惰性初始化27B模型；`get_model_processor(return_dummy_model=True)`实际CPU内存超限137。当前仅对**文本-only**采用官方Transformers5.16.1 `Qwen3_5Model.get_rope_index`的config-only callback，不构建模型权重；任何image/video grid或非零`mm_token_type_ids`必须HOLD。不得把这种文本CPU技术验证当完整多模态训练。
6. `hf_label_mask_audit.audit_row`是严格R18标签门禁，源码内部会产生解码诊断，正式私有Job调用须完全捕获/丢弃stdout/stderr；Job最终日志只发SAFE状态。实际`data_collator`单条batch为二维`(1,T)`，R18旧`_list_ints`只处理一维；用只允许`B=1`、全int的`single_batch_ints`，其余尺寸立即HOLD，保持原始label与input前缀、padding检查。
7. 固定HF原生`chat_template.jinja`在默认`reasoning_effort=xhigh`下自动插入英文system指令；即使指定`medium`，公开合成样本与ms-swift编码仍不等价：medium为16/32 vs Swift12/24，xhigh58/74 vs Swift12/24。**native_template_token_parity_verified=false**，不得虚构System或将技术PASS表述为原生模板完全一致。
8. `SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT`代表源绑定的11条历史实验输入，不等于当年完整真实模型请求。历史实际System/世界卡/记忆不完整，R50 complete exclusion未完成。

## 5. 故障→恢复对照与通过证据

| 证据Job | 事实 | 处理 |
|---|---|---|
| `6af53990ab34849891aecb44` | 镜像被解析为 `docker.io/--name` | 使用符合Homebrew CLI2.4.0的flag顺序和dry-run |
| `6af55aa9ab34849891aed9f4` | `decord` pip check依赖HOLD | 精确豁免+真实导入检查 |
| `6af55dd2ab34849891aedb20` | 模板审核笼统HOLD | 安全阶段码分类 |
| `6af560849737d9a9e093cb46` | `SWIFT_PROCESSOR_LOAD_HOLD` | 显式model_type和template_type |
| `6af56b879737d9a9e093d221` | `SWIFT_COLLATOR_AUDIT_HOLD` | 真实R18合成复现，修正rank2 batch读取 |
| `6af5657cab34849891aeded8` | 无私有CPU dummy-model公开实验OOMKilled137 | 改config-only text RoPE，不提高内存硬顶 |
| `6af566a0ab34849891aedf71` / `6af56c429737d9a9e093d28e` | 公开合成Collator及严格R18 audit验证 | 确认修复方向，不等于真实输入验收 |
| **`6af570089737d9a9e093d501`** | **2026-11-12 07:53:46Z COMPLETED**；最终`R60_CPU2_V2_REAL_COLLATOR_PASS__R50_TRAIN_HOLD` | 实验性私有2条CPU Tokenizer/严格R18/真实Collator技术PASS，训练准入仍0 |

成功RUN_KEY：`r60-common2-cpu2-20261112T073854Z-e076f53c8eae`。所有历史marker、Stage与日志保持；绝不将成功RUN_KEY重新用于提交。公开Issue可记录Job ID和SAFE结论，不能记录私有token ID、原始回复、源关联ID或完整私有SHA。

## 6. 下一阶段和复用边界

对既有成功Job结果应优先**只读**取回`hf://buckets/adradar/storyforge-training/preflight/r60/common2/cpu2/results/<RUN_KEY>/R60_COMMON2_CPU2_SAFE_RECEIPT.json`，验证schema、`cases=2`、Token与Label数量区间、成功状态、`collator_verified=true`、`r50_complete_exclusion_verified=false`、`train_admitted=0`、`gpu_started=false`、`model_weights_loaded=false`、`native_template_token_parity_verified=false`，只输出聚合SAFE。这是已有Job证据回收，不启动任何新Job或覆盖Bucket。若某字段缺失/不符，保留HOLD。回执字节SHA可留Owner私有台账，不要公开源数据摘要。

剩余门禁：真实发送的完整上下文/历史有效System与世界组件；原生Chat Template token不等价的规范决策；R50冻结完整来源集合/故事、session、message与Train候选的交集证明；独立Quality/Owner admission；训练授权。先解决这些门禁，不再为了已经PASS的2条重复花钱跑CPU Probe。任何新的训练、GPU、模型推理都需要显式工作范围，不由本CPU技术PASS自动许可。


## 7. 第五轮已完成Job的 SAFE 回执只读回收命令（当前建议执行）

此处不创建新的RUN_KEY、不提交任何Job。Owner Mac上只从固定成功结果前缀**读取**回执；代码中的KEY必须与成功Job一致。

```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
export PATH="/opt/homebrew/bin:$PATH"
TEST_PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$TEST_PY" -m pytest -q tests/test_r60_common2_cpu2_receipt_verify.py
KEY="r60-common2-cpu2-20261112T073854Z-e076f53c8eae"
BASE="$HOME/.local/share/storyforge/r60/private"
test -d "$BASE"
umask 077
RECEIPT_DIR="$(mktemp -d "$BASE/r60-cpu2-safe-receipt-XXXXXXXX")"
chmod 700 "$RECEIPT_DIR"
RECEIPT="$RECEIPT_DIR/R60_COMMON2_CPU2_SAFE_RECEIPT.json"
REMOTE="hf://buckets/adradar/storyforge-training/preflight/r60/common2/cpu2/results/$KEY/R60_COMMON2_CPU2_SAFE_RECEIPT.json"
# hf buckets cp可读取已有对象；此调用不改远端Bucket。
hf buckets cp "$REMOTE" "$RECEIPT"
test -f "$RECEIPT" && test ! -L "$RECEIPT"
chmod 600 "$RECEIPT"
"$TEST_PY" scripts/r60_common2_cpu2_receipt_verify.py --receipt "$RECEIPT"
```

预期：`CPU2_SAFE_RECEIPT_VERIFIED__R50_TRAIN_HOLD`，输出安全的2条Token/Collator/Supervised计数、固定未准入门禁。任何`CPU2_SAFE_RECEIPT_HOLD`即停，不能更改原始SAFE JSON让它PASS。下载后文件仍在Owner私有0700目录，可供后续只读取证；不要提交GitHub。此脚本只验证业务字段/有限范围、0600权限/普通文件，**不单独证明HF远端对象哈希一致性**；如需传输层完整字节证据，再在Owner私有台账本地计算哈希并将来源URI与HF Job ID绑定，不公开私有输入哈希。上述HF CLI远端→本地`cp`方向是建议操作，需由Owner在实际CLI2.4.0核实；未收到真实回执之前不得标为已完成归档。
