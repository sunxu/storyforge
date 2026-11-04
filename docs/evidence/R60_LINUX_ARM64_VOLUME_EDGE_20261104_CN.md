# R60 Linux ARM64 Volume Edge 测试证据

日期：2026-11-04  
环境：`storyforge-r60-linux:py311`，Linux ARM64，Python 3.11.18，pytest 8.4.2，Ruff 0.14.3  
数据：仅使用合成 JSON；未访问 Gold、R50、R59 私有数据。

## 执行结果

| 检查 | 结果 |
|---|---|
| Ruff（Runtime + 两个测试文件） | PASS |
| compileall | PASS |
| SAFE Volume edge tests | 6 passed |
| Runtime combined tests | 28 passed |
| GPU | 未启动 |
| Training | 未执行 |

## 六项专项结果

1. 并发 create-only 发布：PASS；两个并发写入仅一个成功。
2. 部分写入后模拟 ENOSPC：PASS；未发布目标 SAFE，临时文件清理。
3. 文件 fsync 失败：PASS；临时文件清理。
4. 目录 fsync 失败：PASS；未提交的发布名被回滚。
5. hard-link 不支持：PASS；失败关闭，未发布目标文件。
6. 清理失败：PASS；返回 `OUTPUT_CLEANUP_FAILED`，测试随后恢复清理函数并移除故意遗留的合成临时文件。

## 证据边界

本轮验证的是 Docker Linux ARM64 当前挂载工作区所使用文件系统上的行为，以及测试注入的错误路径。

尚未验证：
- macOS 对新增六项测试的兼容性；
- Linux x86_64；
- HF Jobs 管理的 RO/RW Volume 实际行为；
- HF Volume 同步回 Mac 后的 SAFE 字节、SHA256 和回执验收；
- 真实文件系统耗尽磁盘的端到端表现（本轮通过确定性 ENOSPC 注入测试）。

因此状态为：
`LINUX_ARM64_VOLUME_EDGE_SUITE_PASS__MAC_X86_AND_HF_VOLUME_PENDING`。

HF CPU Smoke 未提交。GPU 与训练未启动。
