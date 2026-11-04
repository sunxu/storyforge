# R60 GitHub Actions Runner 分配阻塞调查

日期：2026-11-04  
仓库：`sunxu/storyforge`（Private）  
PR：#12  
分支：`r60/hf-jobs-runtime`

## 已观察事实

在 PR 当前 HEAD `b5447523c24ce169a3b352b6199eeddebde8f294` 上，两个不同 Workflow 均在 Runner 分配之前失败：

| Workflow | Run ID | Job | 结果 |
|---|---:|---|---|
| R60 HF Runtime CI | 41798030606 | runtime-quality-gates | failure |
| 原有 CI | 41798030595 | test | failure |

通过 GitHub Actions Jobs API 检查：
- 两个 Job 均无 steps（`steps: null` / steps API 返回空数组）。
- Job logs URL 为 null；尝试下载日志返回 BlobNotFound。
- 更早的 Job 快照曾明确显示 `runner_id=0`、`runner_name=""`。
- 两个 Workflow 都使用 `runs-on: ubuntu-latest`，但彼此步骤和权限设置不同。
- R60 workflow 顶层仅声明 `permissions: contents: read`。
- 因原有 CI 也出现同样的 pre-runner failure，当前证据不支持将问题归因于 R60 YAML 或 Runtime 代码。

## 当前诊断结论

状态：
`GITHUB_HOSTED_RUNNER_PRE_ALLOCATION_FAILURE__ACCOUNT_OR_SERVICE_CAUSE_UNCONFIRMED`

这不是测试断言失败；GitHub Actions 尚未运行 checkout、setup-python、pip、Ruff 或 pytest。

目前不能仅凭 `runner_id=0` 确认是账单额度、spending limit、账户付款状态、仓库策略或 GitHub runner 服务问题。日志不可用，根因仍待 Owner 账户侧确认。

调查时 GitHub Status 页面显示 Actions Operational；这只能说明公开状态页当前未报告广泛故障，不能排除账户级限制或个别调度问题。

## Owner 侧只读检查

1. 在 GitHub 账户设置中打开 Billing / Plans and usage / Spending limits，确认 Actions hosted compute 的支出上限是否为 0、是否已达到上限、是否存在付款或账单警告。
2. 在仓库 Settings → Actions → General，确认 Actions 未禁用、允许的 Actions 策略未阻断 `ubuntu-latest`。
3. 使用已登录 gh CLI 查询本账户本月仓库 Actions 使用情况（命令见本报告对应会话交接，不把 token 或账单敏感信息贴入聊天）。
4. 如果 spending limit 和 usage 均正常，向 GitHub Support 提供上述两个 Run ID，请求检查 hosted runner admission / billing entitlement。

## 安全决策

- 不把仓库改为 public。
- 不为排障直接提高 spending limit；先只读核验，再由 Owner 决定。
- 不把 Mac 主机直接注册为常驻 self-hosted runner。Self-hosted runner 可能被工作流代码持久化攻陷，且主机上有其他项目和私有数据。
- 如确需替代方案，只考虑一次性、无凭据、无宿主机敏感目录挂载的隔离 runner 容器；必须单独评审后再实施。
- 不反复 rerun 已知 pre-runner failure。
- HF CPU Smoke 仍不得在 GitHub CI 门禁未解决前启动。

## 证据边界

本报告记录可由 Actions API 复核的运行状态和 Workflow 配置。账户 Billing / Spending Limit 状态尚未读取，GitHub Support 也尚未确认根因。
