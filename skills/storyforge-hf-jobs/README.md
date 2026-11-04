# StoryForge HF Jobs Skill v1.0.0

面向后续 Agent 和开发者的统一 HF Jobs Runtime 操作 Skill。

- [SKILL.md](SKILL.md)：执行顺序、权限边界和公共 API 使用约定。
- [RUNTIME.md](references/RUNTIME.md)：七个模块与接口导航。
- [CPU_SMOKE.md](references/CPU_SMOKE.md)：本地门禁、远端 Smoke 和回执回收。
- [DIAGNOSTICS.md](references/DIAGNOSTICS.md)：诊断 Schema、阶段与隐私规则。
- [SECURITY.md](references/SECURITY.md)：文件、Volume、GPU 和数据安全。
- [TROUBLESHOOTING.md](references/TROUBLESHOOTING.md)：常见失败的定位顺序。
- [cpu_job.py](examples/cpu_job.py)、[safe_receipt.py](examples/safe_receipt.py)、[local_test.py](examples/local_test.py)：调用公共 Runtime 的最小示例。

本 Skill 不包含第二份 Runtime 或 Tokenizer 算法；以公共源码和 `docs/standards/HF_JOBS_ENGINEERING.md` 为权威。
