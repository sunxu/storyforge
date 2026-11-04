# R60 项目审计报告

日期：2026-11-04  
审计基线：`adc3876d6d0350c270e2b5fa5ccc832438fdf7ee`  
审计分支：`r60/hf-jobs-runtime`

## 1. 仓库与 Worktree

GitHub 仓库 `sunxu/storyforge` 为 Private，默认分支 `main`，Owner 具备 push 权限。批准的开发基线分支与 Commit 完全一致。

Owner 在 Mac 提供的 Worktree 清单：

| 路径 | 分支 | HEAD | 状态 |
|---|---|---|---|
| `~/workspace/storyforge` | main | `701ab9c` | clean |
| `~/workspace/storyforge-gold-quality` | gold-quality/quality-v1-sft-candidates | `adc3876` | 有 3 个未跟踪文件 |
| `~/workspace/storyforge-r55-tooling` | r57/v03b-data-design | `4dd144d` | 有 1 个未跟踪文件 |
| `~/workspace/storyforge-r59-strict28-exposure-20261103` | r59/strict28-history-exposure | `a458bb2` | clean |
| `~/workspace/storyforge-r60-hf-jobs-runtime` | r60/hf-jobs-runtime | `cbfb3cd`（创建时） | clean |

R60 Worktree 已从远端 R60 分支创建。其后远端继续提交代码，Mac Worktree 需要 fast-forward 更新。R60 Agent 未触碰其他 Worktree 的未跟踪文件。

## 2. 可复用工程能力

- `src/storyforge_dataset/token_preflight.py`：共享 Tokenizer 算法核心。批准基线与 R60 分支 Blob SHA 均为 `9ea7596c2151ee10aa1394beedc36ffeb9a7fca8`，未修改。
- `scripts/hf_job_guard.py`：CPU Job 提交策略 Guard，继续负责 namespace、CPU flavor、Volume 模式、timeout 与单次提交约束。
- `docs/HF_JOBS.md`：历史 HF CLI、Volume 挂载、RW Smoke 和同步回收规范。
- `docs/standards/HF_TOKEN_PREFLIGHT_REUSE_CN.md`：共享 Tokenizer 核心复用契约。
- `pyproject.toml`：Python `>=3.11`，核心依赖为空，开发依赖为可选项。
- `.github/workflows/ci.yml` 与 `.github/workflows/r58-scoped-synthetic.yml`：现有 CI 基础设施。

## 3. Worktree 与远端差异

本轮通过 GitHub 只读 API 核验远端基线、分支、Commit 和文件 Blob。Owner 提供的本地 Worktree 状态用于确认 R60 Worktree 已安全创建。Agent 执行环境无法直接访问 Owner Mac 文件系统，因此后续本地测试由 Owner 在新 Worktree 中执行并回传输出。

## 4. CI 观察

R60 PR #12 已创建为 Draft。GitHub Actions 多次创建 Workflow Run，但 Job 返回 `runner_id=0`、空 `runner_name`、空 `steps`，约 2–3 秒即结束。现有仓库 CI 同样出现该现象。当前证据指向 Runner 未分配，不能将其解释为 Runtime 测试断言失败；也不能将其解释为 CI PASS。

## 5. 审计结论

- 基线与远端分支：VERIFIED。
- Owner Worktree 隔离：按提供的清单 VERIFIED。
- R60 专属 Worktree：CREATED，创建时 clean。
- Tokenizer 核心未改动：VERIFIED。
- Runtime 代码测试：PENDING。
- GitHub CI：BLOCKED_BEFORE_RUNNER_ALLOCATION。
- HF CPU Smoke：NOT RUN。
- GPU / 训练：未启动。
