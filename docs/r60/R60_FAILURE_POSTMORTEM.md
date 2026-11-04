# R60 故障复盘

## 1. 范围

本报告复盘 R59 交接中已观察到的六类基础设施故障。由于没有在 R60 中读取或重新运行 R59 私有输入，本报告区分已知现象与待验证根因，不对历史私有任务作新的推断。

## 2. 故障分类

| 故障 | 已知问题方向 | R60 防护 |
|---|---|---|
| Worktree 被误判不存在 | `.git` 在普通仓库是目录，在 Worktree 是文件 | 不以 `.git` 目录类型作为仓库判定；Git 元数据检查与容器路径分离 |
| Runner Host/Container 路径混淆 | Mac 文件路径与容器入口路径混用 | `ResolvedPath.kind` 显式区分 host/container；禁止安全路径使用 auto 推断 |
| `token_core` 无法导入 | Runner 与 Volume 的 Python 模块搜索路径不一致 | 显式 Bootstrap Source Root；检查包目录和 `__init__.py` |
| SAFE 输出写入失败 | 对挂载权限位作过强假设 | 真实创建、写入、fsync、权限验证；不递归 chmod；失败时报告明确错误 |
| RO 输入读取失败 | HF Volume 权限元数据与本地文件权限假设不同 | descriptor + fstat + no-follow + size + SHA256；权限位不代表内容完整性 |
| 失败只返回 HOLD | 异常阶段和错误类型被合并 | 固定阶段、注册错误码、SAFE 诊断结构；不输出异常正文 |

## 3. 关键安全原则

- 输入内容完整性由安全打开的文件描述符、大小限制、读取前后身份信息和 SHA256 建立。
- 文件权限、owner、link count 是文件系统元数据，不可单独证明内容可信。
- 输出必须 create-only；不允许覆盖已有 SAFE。
- 原子发布和权限保证若在目标文件系统不可用，必须失败关闭，不得静默降级。
- 诊断回执不得包含原始输入、异常消息、完整环境变量、凭据或任意私有路径。

## 4. 待验证事项

- HF 管理 Volume 是否支持 `O_NOFOLLOW`、`fchmod`、hard-link 原子发布和目录 fsync。
- macOS 与 Linux 对目录 fsync 的差异。
- R59 历史六类故障能否被对应本地测试稳定复现。
- HF CPU Smoke 是否能在真实 RO/RW Volume 中通过。

以上事项在真实文件系统验证前均为 PENDING。
