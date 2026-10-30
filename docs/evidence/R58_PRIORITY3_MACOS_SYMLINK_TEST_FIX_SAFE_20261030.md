# R58 Priority3 — macOS 合成测试路径别名修复（SAFE）

日期：2026-10-30。收到 Owner 上传的终端测试日志。**用户本机实际结果：17 项中 1 PASS、14 FAIL、2 ERROR**；16 个异常均为 `capture_priority3.Hold: symlinked path component forbidden`。未运行生产数据导出。

## 根因分析

`test_capture_priority3.py` 的 `tempfile.TemporaryDirectory()` 在 macOS 常位于 `/var/folders/...`。macOS 默认系统目录 `/var` 是指向 `/private/var` 的 symlink。原 `safe_existing_parent` 对父目录的每一层执行 `is_symlink()` 并一律拒绝，使所有正常的临时测试路径在触及案例数据校验前就被拒绝。

这是一处 macOS 路径兼容缺陷。它不证明生产数据、数据库权限或 SFT 样本错误。

## 最小修复

- `experiments/r58_roleplay_replay/capture_priority3.py` 新增 `_trusted_macos_system_link()`：**仅在 `sys.platform == 'darwin'`**，仅接受 `/var` 与 `/tmp` 这两个固定绝对路径，且 `resolve(strict=True)` 分别等于 `/private/var` 与 `/private/tmp` 的既定目标。所有其他 symlink 仍触发 HOLD。
- `test_capture_priority3.py` 增加 `test_macos_system_temp_alias` 和 `test_untrusted_ancestor_symlink`；由 17 增至 **19** 个测试（在 Linux 运行时前者明确 SKIP）。
- 已在 Linux 隔离容器对等价的路径检查代码做小范围检查：私有父目录通过、直接 symlink 拒绝、中间父目录 symlink 拒绝、不安全权限拒绝。**不是仓库全量 19 项测试，也不能替代 Owner 的 macOS 复测。**

## 接受条件

Owner 在 Mac 上执行：

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
python3 -m unittest discover -s experiments/r58_roleplay_replay -p 'test_capture_priority3.py' -v
```

预期 `Ran 19 tests`，`OK`。如仍失败，保持 `HOLD` 并提供脱敏 traceback；在完整通过前**不要执行** `PRIVATE_PRIORITY3_QUARANTINE_EXPORT_TEMPLATE.sql` 的生产数据捕获。

本轮仅提交 GitHub R58 实验代码和 SAFE 报告，无 Supabase/数据库写入、无 HF Job、无 R50 操作；PR #7 继续 Draft、Skill v0.1 不变、v0.4 Train/Val 0。
