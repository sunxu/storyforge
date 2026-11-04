# Runtime API 导航

权威实现：`src/storyforge_dataset/hf_runtime/`。本页只说明职责，不复制实现。

| 模块 | 职责 | 主要 API |
|---|---|---|
| context.py | 环境识别与安全环境摘要 | `RuntimeContext.detect`, `to_safe_dict` |
| paths.py | Host/Container 路径显式解析 | `PathResolver.resolve`, `validate_input_root`, `validate_output_root` |
| inputs.py | no-follow 打开、限长读取、SHA256、JSON/JSONL | `InputManager.open_verified`, `validate_json`, `validate_jsonl` |
| outputs.py | 输出能力探针、SAFE create-only 原子发布 | `OutputManager.probe`, `write_safe` |
| diagnostics.py | 阶段、稳定错误码、隐私安全诊断 | `DiagnosticReporter` |
| resources.py | CPU Profile 与 GPU 拒绝检查 | `ResourceGuard.check_cpu_only`, `check_profile` |
| receipts.py | Runtime 诊断回执校验 | `ReceiptValidator.validate_runtime_receipt`, `verify_file` |

CLI：`python -m storyforge_dataset.hf_runtime doctor --profile cpu --json`。

Runtime 使用 Python 3.11 标准库，不依赖 Transformers、PyTorch、ms-swift、HF Hub 或网络。不要在公共 Runtime 中添加业务逻辑、模型导入、Job 提交或数据准入。
