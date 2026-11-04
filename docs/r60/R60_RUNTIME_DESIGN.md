# R60 Runtime 设计摘要

完整冻结契约见 `docs/standards/R60_HF_JOBS_RUNTIME_ARCHITECTURE_V1_CN.md`。

## 模块边界

| 模块 | 责任 |
|---|---|
| `context.py` | 识别 LOCAL / CONTAINER / HF_JOB / TEST，输出有限安全环境字段 |
| `paths.py` | 显式 Host/Container 路径类型、路径校验、Runner Source Root Bootstrap |
| `inputs.py` | no-follow 文件描述符读取、大小限制、SHA256、JSON/JSONL 结构检查 |
| `outputs.py` | 输出目录能力探测、0600 SAFE 文件、create-only 原子发布 |
| `diagnostics.py` | 阶段、错误码、隐私安全诊断 |
| `resources.py` | CPU profile 检查，不导入 CUDA、不启动资源 |
| `receipts.py` | Runtime Diagnostic Receipt 严格 Schema 验证 |

## 公共调用

```python
from pathlib import Path
from storyforge_dataset.hf_runtime import (
    RuntimeContext, PathResolver, InputManager,
    OutputManager, ResourceGuard, DiagnosticReporter,
    ReceiptValidator,
)

context = RuntimeContext.detect(profile="cpu")
ResourceGuard.check_cpu_only()
source_root = PathResolver.bootstrap_module_root(Path("/data"))
verified = InputManager.open_verified(
    Path("/job/synthetic.jsonl"), max_bytes=1024 * 1024
)
records = InputManager.validate_jsonl(verified.read_bytes(), max_records=100)
```

## Doctor

```bash
python -m storyforge_dataset.hf_runtime doctor --profile cpu --json
```

Doctor 仅执行环境检查、CPU 资源检查和隔离临时目录写入探测；不访问业务输入、网络、模型、私有 Volume 或 GPU。

## 安全约束

- Runtime 不负责 HF Job 提交。
- Runtime 不负责业务数据质量或训练准入。
- 不接受自动路径猜测。
- 不覆盖 SAFE 文件。
- 任何目标文件系统不支持的安全属性必须明确失败。
