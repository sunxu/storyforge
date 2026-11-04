# R60 实施计划与阶段门禁

| 阶段 | 交付 | 门禁 |
|---|---|---|
| R60-00 | GitHub / Worktree 审计、现有组件清单、故障复盘 | 基线 SHA 与 Worktree 隔离确认 |
| R60-01 | Architecture Baseline v1.0 | Owner 已批准 |
| R60-02 | 七模块 Runtime、doctor、合成单元测试 | Mac 本地 lint / compile / pytest PASS |
| R60-03 | Linux 与 macOS Volume 语义测试 | 文件权限、symlink、hardlink、SHA、原子写入测试 PASS |
| R60-04 | 隐私诊断、ResourceGuard、Receipt Validator | Schema 与安全测试 PASS |
| R60-05 | GitHub Actions 独立 CI | 所有必需 checks PASS |
| R60-06 | HF CPU Smoke | 仅在本地门禁与 CI 全 PASS 后执行；cpu-basic、一次、合成数据 |
| R60-07 | 工程标准和 HF Jobs Skill | 示例引用公共 Runtime，不复制实现 |
| R60-08 | R59 Adapter 迁移验证 | 冻结 Prompt 与输入字节不变；Tokenizer CPU PASS |
| R60-09 | 最终验收和交接 | Draft PR 审核、Owner 合并审批 |

## 当前状态

- R60-00：GitHub 基线、目标分支和 Owner 提供的 Worktree 快照已核验；审计文档已提交。
- R60-01：Architecture Baseline v1.0 已批准并提交。
- R60-02：七模块首版和合成测试已提交；Mac 本地测试尚未运行。
- GitHub Actions：Workflow Job 创建但 Runner 未分配（`runner_id=0`、无 steps）；当前不能判定测试通过或失败。
- HF CPU Smoke：NOT RUN。
- GPU / Training：禁止且未执行。

## 下一道门禁

在 Mac 专用 Worktree fast-forward 到最新 R60 分支后，执行本地测试命令并回传完整退出码。修复所有本地问题，再恢复 GitHub CI Runner。未满足两项门禁前不提交付费 HF Job。
