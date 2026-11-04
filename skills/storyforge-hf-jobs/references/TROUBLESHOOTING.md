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
| `TOKENIZER_LOAD_FAILED` | 模型 ID、不可变 Revision、依赖版本、网络/缓存 | 改用未固定 Revision |
| `CHAT_TEMPLATE_FAILED` | Jinja2、Tokenizer 模板与共享核心版本 | 改写 prompt 或截断历史 |
| SAFE 回执缺失 | Job 日志、OUTPUT_WRITE 阶段、Bucket 目标路径 | 仅凭 Job COMPLETED 宣告 PASS |

诊断报告应只保留阶段、稳定错误码、异常类型和经审查的非敏感元数据。不要把完整异常消息或堆栈提交公开 CI。
