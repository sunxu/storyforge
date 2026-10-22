# R50 CPU46 — Transformers v5 `BatchEncoding` 兼容性离线热修

Owner 报告旧 Job `6ada3836c191903149a7332a` 的私有 stderr 出现 `TypeError: invalid encoded ids for ...`。Transformers v5 的 `apply_chat_template()` 默认结果由 `list[int]` 改成了 `BatchEncoding`（迁移指南：<https://github.com/huggingface/transformers/blob/main/MIGRATION_GUIDE_V5.md>）。**实际源码需经本工具的 AST 验证，不因单条报错直接确认具体原因**。

本工具不读取 R50 案例、System 或报告，不导入 Transformers，不连接网络，也不启动任何 HF Job。它只修改先前**原始私有**预检脚本的一份副本，在唯一一个符合条件的 `apply_chat_template()` 调用尾部显式加 `return_dict=False`，保证原 AST 只发生这一处行为修改。若原件 SHA256 不符合用户机器回执，或调用结构不符合保守条件，则阻断。

## Mac 操作（纯 Python 标准库，无 Transformers）

```bash
cd ~/workspace/storyforge
git pull --ff-only origin main
python3 -m unittest discover -s tests -p 'test_v03_r50_v5_return_dict_hotfix.py' -v
umask 077
OLD='r50-cpu46-20261022T161724Z-363451'
SOURCE="$HOME/.local/share/storyforge/r50/hf-cpu46/$OLD/stage/private/R50_CPU_TOKENIZER_PREFLIGHT_46.py"
NEW="$HOME/.local/share/storyforge/r50/preflight-v5-compat-copy-20261023/R50_CPU_TOKENIZER_PREFLIGHT_46.py"
python3 scripts/v03_r50_v5_return_dict_hotfix.py --source "$SOURCE" --output "$NEW"
```

成功输出 `PRIVATE_PREFLIGHT_PATCHED_COPY__NOT_RUN_ON_HF` 和新的脚本 SHA256。若输出 `HOLD`，**不要重新 Sync**，先复查程序实际形态。

之后用新的私有脚本副本（仅仅 sync，不 submit）：

```bash
R50_PREFLIGHT="$NEW" bash scripts/v03_r50_hf_cpu46_submit.sh sync
```

新 RUN_KEY 必须由 sync 生成；此前失败的 RUN_KEY 不得复用。审核原始 46 条来源及 R45 系统 SHA 保持原样，新的预检脚本 SHA 单独冻结到新 Stage。

**变更范围限制：** 这只是 V5 API 结构兼容修复，不保证所有 46 题的长度、连续 User 模板或正式 Held-out 准入。新的 CPU Job 如果需要执行，必须再次取得单独付费授权。任何原始故事或私有预检脚本内容都不得进入 Git。
