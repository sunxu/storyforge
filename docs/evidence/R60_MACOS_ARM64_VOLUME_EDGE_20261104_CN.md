# R60 macOS ARM64 Volume Edge 测试证据

日期：2026-11-04  
环境：macOS Darwin ARM64，Python 3.11.15，pytest 8.4.2，Ruff 0.14.3  
Worktree：`~/workspace/storyforge-r60-hf-jobs-runtime`  
分支：`r60/hf-jobs-runtime`  
测试数据：仅合成 SAFE JSON；未访问 Gold、R50、R59 私有数据。

## 执行结果

| 检查 | 结果 |
|---|---|
| Git fast-forward 同步 | PASS |
| Ruff | PASS |
| SAFE Volume edge tests | 6 passed |
| Runtime combined tests | 28 passed |
| GPU | 未启动 |
| Training | 未执行 |

## 六项专项结果

1. 并发 create-only 发布：PASS。
2. 部分写入后模拟 ENOSPC：PASS。
3. 文件 fsync 失败清理：PASS。
4. 目录 fsync 失败回滚：PASS。
5. hard-link 不支持时失败关闭：PASS。
6. 清理失败显式诊断：PASS。

## 跨平台结论

同一组 SAFE Volume edge tests 已在以下两个本地环境通过：

- Linux ARM64 / Python 3.11.18：6/6；Runtime combined 28/28。
- macOS ARM64 / Python 3.11.15：6/6；Runtime combined 28/28。

这证明当前代码路径在上述两种本地环境通过合成测试，但不等于验证了 HF 管理 Volume 的真实挂载语义。

## 未覆盖范围

- Linux x86_64。
- HF Jobs 管理的 RO/RW Volume。
- HF Volume 回收同步后的 SAFE 字节、SHA256 和回执验证。
- 真实磁盘耗尽的端到端测试（本轮为确定性 ENOSPC 故障注入）。

状态：
`MAC_AND_LINUX_ARM64_VOLUME_EDGE_PASS__X86_AND_HF_VOLUME_PENDING`。

HF CPU Smoke 未提交。GPU 与训练未启动。
