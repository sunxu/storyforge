# 故障定位顺序

先读取 SAFE 诊断字段，不读取或回显私有输入。完整错误码以公共 Runtime 注册表为准。

| 现象/错误码 | 首要检查 | 不允许的绕过 |
|---|---|---|
| `RUNTIME_ENVIRONMENT_UNKNOWN` | Job 环境标志、容器识别来源 | 手工伪造 HF_JOB |
| `PATH_KIND_AMBIGUOUS` | Host/Container 参数是否显式 | 将 /job 当成本机路径 |
| `INPUT_OPEN_FAILED` | 挂载目录、文件名、RO 模式、文件存在性 | 放宽 symlink 检查 |
| `INPUT_SHA256_MISMATCH` | 本地输入字节、上传后远端 SHA | 更新期望 SHA 来掩盖差异 |
| `INPUT_DESCRIPTOR_CHANGED` | 文件是否在读取时被替换/修改 | 忽略 descriptor 检查 |
| `OUTPUT_PROBE_FAILED` | 独立 RW 输出挂载、权限与真实写探针 | 递归 chmod/chown Bucket |
| `OUTPUT_ALREADY_EXISTS` | 唯一输出前缀和历史回执 | 覆盖或删除旧 SAFE |
| `OUTPUT_ATOMIC_PUBLISH_UNSUPPORTED` | 文件系统原子 no-replace 能力 | 降级为普通覆盖写 |
| `CPU_PROFILE_GPU_VISIBLE` | Flavor、ACCELERATOR、CUDA/NVIDIA 设备 | 只清空 CUDA_VISIBLE_DEVICES 后继续 |
| `HF_CPU_RESOURCE_GUARD_HOLD`（在 vLLM GPU 镜像的 CPU-basic Job） | 检查 `ResourceGuard.check_cpu_only().checks`：`ACCELERATOR`、`CUDA_VISIBLE_DEVICES`、`NVIDIA_VISIBLE_DEVICES`、实际 `/dev/nvidia*` 设备、`torch.cuda` 导入。GPU 基础镜像的 `NVIDIA_VISIBLE_DEVICES` 可能默认非空，即使 CPU-basic 没有 GPU 设备；须拿到 SAFE 子检查再判定 | 仅清空 CUDA 隐藏实际 GPU、修改 ResourceGuard 放宽检查、或无子码重复付费提交 |
| `TOKENIZER_LOAD_FAILED` | 模型 ID、不可变 Revision、依赖版本、网络/缓存 | 改用未固定 Revision |
| `CHAT_TEMPLATE_FAILED` | Jinja2、Tokenizer 模板与共享核心版本 | 改写 prompt 或截断历史 |
| `HF_CPU_CHAT_TEMPLATE_RENDER_FAILED_CLASS_IMPORTERROR` | 优先核对历史 R58 已证实的 Jinja2 缺失问题；CPU 包须含 `transformers==4.57.1`、`jinja2==3.1.6`、`sentencepiece==0.2.1`，先 `pip check` 与无私有文本的 import smoke | 新建多版诊断 Worker、重跑未变输入、绕过模板 |
| SAFE 回执缺失 | Job 日志、OUTPUT_WRITE 阶段、Bucket 目标路径 | 仅凭 Job COMPLETED 宣告 PASS |

诊断报告应只保留阶段、稳定错误码、异常类型和经审查的非敏感元数据。不要把完整异常消息或堆栈提交公开 CI。


**2026-11-08 回归教训**：R58 已于 2026-11-01 解决同一 Jinja2 ImportError，R60 未复用其验证依赖基线，导致连续多次付费 CPU HOLD。先复用 `docs/standards/HF_TOKEN_PREFLIGHT_REUSE_CN.md` 中的依赖组合；不要把 Guard 的本地配置 PASS 当成云端 Tokenizer PASS。提交前先 `--check-hf-cli`、原生 `--dry-run`，运行时必须显式安装 Jinja2 并执行 import/pip check。只有 HF 真实 Tokenizer SAFE 才可推进。


**2026-11-08 R60 双槽案例**：固定 vLLM GPU digest 的 `cpu-basic` 兼容性预检 A/B 两 Job（`6af04c570e0338d1bb84a91e` / `6af04c58e6320c66fad7416c`）均在 `HF_GPUIMAGE_DEPS_PRESENT` 后输出 `HF_CPU_RESOURCE_GUARD_HOLD`，未进入 Tokenizer。历史 CPU 标准镜像 A/B 各 1000/1000 Tokenizer PASS 不受影响。不要把失败误认为数据或模型评审问题。下一次仅 A 用独立输出前缀，在不修改公共 ResourceGuard 的条件下读取 SAFE `checks`；若实际 GPU 设备节点、非 CPU ACCELERATOR 或 CUDA 模块出现，立即 HOLD。仅当是容器默认的 NVIDIA 可见性变量且**无 GPU 设备**时，可在 CPU Job 的 shell 中明确 `NVIDIA_VISIBLE_DEVICES=void`，然后重新运行完整 ResourceGuard，再运行 Tokenizer（仍是 CPU flavor）。先 A 后 B，不要同时盲重试两槽。


**2026-11-08 R60 A 精确证实**：GPU vLLM 固定 digest 运行于真正 `cpu-basic` 时，原始 `ResourceGuard` SAFE 子项均 PASS，唯 `nvidia_visibility=FAIL`；当且仅当另外四项 PASS（包含实际无 NVIDIA 设备节点），在 shell `export NVIDIA_VISIBLE_DEVICES=void` 后完整资源检查五项全部 PASS，随即同镜像 A 真正 1000/1000 CPU Tokenizer PASS（over_budget=0）。HF Job `6af04eb10e0338d1bb84a9e1` 终态 COMPLETED，证据 `docs/evidence/R60_GPUIMAGE_A_CPU1000_ENVFIX_PASS_SAFE_20261108.json`。**不允许从此推断 GPU 节点上的检查可忽略，更不允许更改 ResourceGuard 以放松安全标准**。后续 B 参照 A 已验证的步骤单槽进行，新的独立输出，禁止重复提交 A。
