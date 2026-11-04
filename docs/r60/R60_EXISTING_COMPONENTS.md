# R60 现有组件复用清单

| 组件 | 当前职责 | R60 决策 |
|---|---|---|
| `token_preflight.py` | Tokenizer 输入编码、统计和摘要算法 | 保留原样，唯一共享核心 |
| `hf_job_guard.py` | HF CPU Job 提交策略 | 保留，不将提交功能搬进 Runtime |
| `docs/HF_JOBS.md` | HF CLI、Volume、Smoke、同步经验 | 作为操作规范来源，后续补充 Runtime 使用方法 |
| `HF_TOKEN_PREFLIGHT_REUSE_CN.md` | Tokenizer 共享核心和 Adapter 契约 | 保留，Runtime 不复制算法 |
| R57 `hf jobs uv run` 流程 | 本地 Volume 同步与任务执行 | 保留历史成功路径，作为后续 Smoke 设计参考 |
| R58 RW Smoke | Mac CLI 私有 Bucket RW 和同步回收 | 保留历史证据，远端 Smoke 复用其 Volume 拓扑 |
| R59 SAFE receipt | 业务级 SAFE 回执 | 作为迁移参考，不直接成为 Runtime 公共实现 |
| R59 CPU Tokenizer Runner | Tokenizer 业务任务 | 后续迁移到公共 Runtime 的 Adapter，不改冻结 Prompt |

## 不应重写的内容

1. Tokenizer 编码和 token budget 算法。
2. 已验证的 HF namespace / bucket / RO+RW 分离策略。
3. R58/R59 历史任务的冻结输入、Prompt、输出及证据。
4. 现有提交 Guard 的 CPU flavor、单次提交和禁止 namespace fallback 策略。

## 需要新增的能力

- 统一 RuntimeContext。
- Host / Container Path Resolver 和 Runner bootstrap。
- 安全输入打开、摘要和 JSON/JSONL 结构验证。
- create-only SAFE 输出。
- 统一 Diagnostics 和 Receipt Validator。
- CPU ResourceGuard。
- `doctor --profile cpu --json`。
- 合成文件系统测试和独立 CI。
