# 诊断与回执约定

Runtime 诊断 Schema：`storyforge-hf-runtime-diagnostic-v1`。

顶层字段由 `ReceiptValidator` 严格校验：schema、runtime_version、profile、status、phase、error_code、checks、environment、private_values_emitted、gpu_started、training_performed。

标准阶段与错误码的完整注册表见 `src/storyforge_dataset/hf_runtime/diagnostics.py` 和 `docs/standards/HF_JOBS_ENGINEERING.md`。不要在业务 Skill 中另造公共错误码。

- 状态仅 PASS/HOLD/FAIL；检查仅 PASS/FAIL/UNKNOWN。
- 只输出 allowlisted 字段和非敏感平台元数据。
- 禁止原始 Prompt、历史文本、逐案 ID、凭据、DSN、HF Token、异常正文、堆栈和任意路径。
- 业务 SAFE 回执使用独立业务 Schema；Runtime 诊断回执不能代替业务状态。
- SHA256 证明字节一致，不证明授权、质量、语义正确或训练准入。
