# R60 GitHub Actions CI 恢复与通过证据

日期：2026-11-04  
仓库：`sunxu/storyforge`  
PR：#12  
分支：`r60/hf-jobs-runtime`  
PR HEAD：`be7208b5df08c533863d3c911b3c4a9c78d2e542`

## R60 专项 CI

- Workflow：R60 HF Runtime CI
- Run ID：`41798395598`
- Job ID：`126469060396`
- 结果：`success`
- Runner：GitHub-hosted Ubuntu 24.04 x86_64
- Python：3.11.17
- Runner version：2.338.2

实际执行步骤均完成：

| 步骤 | 结果 |
|---|---|
| Set up job / hosted runner allocation | PASS |
| actions/checkout@v4 | PASS |
| actions/setup-python@v5 | PASS |
| Install package and test tools | PASS |
| Runtime lint | PASS |
| Python compile | PASS |
| Runtime synthetic tests | 28 passed |
| Shared token_preflight core regression | 8 tests OK |
| Runtime dependency boundary | PASS |
| Complete job | PASS |

日志关键输出：
- Ruff：`All checks passed!`
- pytest：`28 passed in 0.22s`
- unittest：`OK`
- Runtime dependency boundary：`PASS`

CI 实际 checkout PR merge ref `d6704e1bf788c3227a0a8bf68a5b734883799a68`，即 PR HEAD 与目标基线的合并测试结果，而非仅在本地分支运行。

## 旧有仓库 CI

同一 PR HEAD 上的旧有 CI Run `41798395317` 在 08:17Z 失败，未执行 steps。R60 专项 CI 于 08:20Z 成功，证明 Hosted Runner 随后已能正常分配。

为确认恢复后旧有 CI 是否也能运行，已对原失败 Job 执行一次定向重跑：
- 新 Job ID：`126469568034`
- 当前状态：`QUEUED`
- 不重复运行已成功的 R60 专项 Job。

旧有 CI 重跑最终结果需另行记录。

## 跨平台证据汇总

- macOS ARM64 / Python 3.11.15：Runtime 28/28；Volume edge 6/6。
- Linux ARM64 / Python 3.11.18：Runtime 28/28；Volume edge 6/6。
- GitHub-hosted Linux x86_64 / Python 3.11.17：Runtime 28 passed；Token preflight regression 8 tests OK。

这些测试均为合成数据和本地文件系统/CI 环境验证，不等于真实 Hugging Face managed Volume 验证。

## 安全边界

- 未启动 HF Job。
- 未使用 GPU。
- 未执行训练。
- 未读取或修改 Gold、R50、R59 冻结私有数据。
- `token_preflight.py` 保持原样，执行其现有回归测试。

状态：
`R60_GITHUB_HOSTED_CI_PASS__LEGACY_CI_RERUN_PENDING__HF_VOLUME_PENDING`
