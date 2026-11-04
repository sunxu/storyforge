# R60 Handoff — HF Jobs Runtime

更新日期：2026-11-04  
分支：`r60/hf-jobs-runtime`  
PR：[#12 — R60 shared HF Jobs Runtime](https://github.com/sunxu/storyforge/pull/12)（Draft）

## 当前结论

- R60-00 至 R60-06：核心 Runtime、真实 HF CPU Volume Smoke、CI 已验证。
- R60-06：CPU Tokenizer requirements lock 已生成并通过 hash-verified clean install。
- R60-07：`skills/storyforge-hf-jobs/` 已建立，工程标准与 AGENTS 路由已更新。
- R60-08：R59 Pilot8 Tokenizer Runner 已迁移到公共 Runtime；合成测试 PASS，真实 R59 CPU Tokenizer Job 尚未运行。
- R60-09：未完成；PR 保持 Draft，不自动合并。

## 最新证据

### 真实 R60 HF CPU Smoke

- Job：`6aeaf0c3c78863f9c6323e15`
- Flavor：`cpu-basic`
- Python：3.11.18
- SAFE：907 bytes
- SHA256：`d66e2685c5420ea9e2cf0ded7aa5768e67b371df906aae865eb93adc3213d6f1`
- Owner Mac 下载回收：907 bytes，SHA256 MATCH。

### GitHub CI

最新 R60 专项 CI：
- Run：`41807222182`
- 37 Runtime/Volume tests passed
- 10 CPU Smoke adapter tests passed
- 3 Skill contract tests passed
- 7 R59 adapter unit tests passed
- 8 shared token_preflight regression tests passed
- Ruff、Compile、dependency boundary PASS

全仓 CI：
- Run：`41807222067`
- 671 passed，5 skipped，24 subtests passed

独立 R58 scoped synthetic workflow：
- Run：`41805972728`
- `r58-synthetic` 在 `test_secure_output_private_only` 失败，错误 `STAGING_RECEIPT_MISMATCH`。
- 失败测试与 binder 文件在 R60 分支和开发基线的 Git Blob SHA 完全相同；R60 没有修改它们。
- 状态仍为独立 HOLD，不得报告整个仓库所有 Workflow 全绿。

## Owner Mac 下一步命令

不重新创建或安装 Python 环境；复用已有 `~/.venvs/storyforge-r60`。先确认 Worktree 干净，避免覆盖未提交工作：

```bash
set -euo pipefail

cd ~/workspace/storyforge-r60-hf-jobs-runtime

git status --short
if [ -n "$(git status --porcelain)" ]; then
  echo "STOP: worktree has uncommitted changes; preserve and inspect them first."
  exit 1
fi

git fetch origin
git pull --ff-only origin r60/hf-jobs-runtime

source "$HOME/.venvs/storyforge-r60/bin/activate"
python --version
ruff --version
```

运行 R60 / R59 本地合成回归：

```bash
set -euo pipefail

ruff check \
  src/storyforge_dataset/hf_runtime \
  tests/test_hf_runtime.py \
  tests/test_hf_runtime_volume_edges.py \
  tests/test_r60_cpu_volume_smoke.py \
  tests/test_r60_hf_skill_contract.py \
  experiments/r60_hf_runtime/r60_cpu_smoke.py \
  experiments/r58_quality/r59_semantic_prompt_token_cpu.py \
  experiments/r58_quality/test_r59_semantic_prompt_token_cpu.py

python -m compileall -q \
  src/storyforge_dataset/hf_runtime \
  tests/test_hf_runtime.py \
  tests/test_hf_runtime_volume_edges.py \
  tests/test_r60_cpu_volume_smoke.py \
  tests/test_r60_hf_skill_contract.py \
  experiments/r60_hf_runtime \
  experiments/r58_quality/r59_semantic_prompt_token_cpu.py \
  experiments/r58_quality/test_r59_semantic_prompt_token_cpu.py

pytest -q \
  tests/test_hf_runtime.py \
  tests/test_hf_runtime_volume_edges.py \
  tests/test_r60_cpu_volume_smoke.py \
  tests/test_r60_hf_skill_contract.py

PYTHONPATH=experiments/r58_quality python -m unittest discover \
  -s experiments/r58_quality \
  -p 'test_r59_semantic_prompt_token_cpu.py' -q

python -m unittest discover -s tests -p 'test_token_preflight_core.py' -q

python -m storyforge_dataset.hf_runtime doctor --profile cpu --json
```

核对共享 Tokenization 核心未变：

```bash
BASE_BLOB=$(git rev-parse adc3876d6d0350c270e2b5fa5ccc832438fdf7ee:src/storyforge_dataset/token_preflight.py)
HEAD_BLOB=$(git rev-parse HEAD:src/storyforge_dataset/token_preflight.py)
printf 'base=%s\nhead=%s\n' "$BASE_BLOB" "$HEAD_BLOB"
test "$BASE_BLOB" = "$HEAD_BLOB"
```

## 后续 R59 CPU Job 的门禁

只有 Owner Mac 上述命令全部通过后，才进入真实 R59 Tokenizer CPU Job 准备。执行前还必须：

1. 确认当前冻结 Pilot8 Prompt、模型 ID/Revision、预算和输入 SHA/fingerprint；不修改任何值。
2. 将私有输入放入受控私有 RO Bucket；不上传 GitHub，不写入 Job command 或日志。
3. 通过 HF protected secrets 注入 `R59_INPUT_SHA256` 与 `R59_PROMPT_FINGERPRINT`。
4. 安装与 Runner 完全相同的 Git Commit，使 `storyforge_dataset.hf_runtime` 可导入；`token_core.py` 必须与共享核心逐字节相同。
5. 使用独立 RW 输出目录，写入 R59 业务 SAFE 和 Runtime diagnostic SAFE 两个不同文件。
6. 回收两个 SAFE，分别验证 Schema、业务状态、字节数和 SHA256。

该 Job 只运行 CPU Tokenizer，不加载模型权重、不推理、不使用 GPU、不训练、不做 Quality-v1 admission。没有 R59 私有输入时保持 NOT RUN，不用合成输入冒充真实 Pilot8 结果。

## 仍然开放的问题

- Python 3.11 容器镜像的实际 Digest 尚未由历史 Job 元数据证明；不能将 `python:3.11` Tag 当作不可变镜像。
- 完整 HF CPU 依赖解析锁仍需单独完成；Runtime 核心本身无第三方运行时依赖。
- R58 scoped synthetic 的 `STAGING_RECEIPT_MISMATCH` 需独立调查。
- R59 真实 CPU Tokenizer 与双 SAFE 回执回收尚未执行。
- GPU authorization：NONE；不得推导为 GPU inference/training 授权。


## 2026-11-04 macOS host-path compatibility fix

Owner's first local run passed Ruff, 48 Runtime/Volume/Skill tests, shared token_preflight 8/8, CPU doctor, and immutable-core comparison. Two R59 adapter tests failed because macOS temporary paths traverse an OS-managed symlink ancestor (commonly `/var -> /private/var`), which the HF managed-mount root validator correctly rejects.

Fix commit: `ddf2ea3419fb2f0a1b772e0ff0c54aed065fe5c0`.
- R59 helper defaults now use strict `path_kind="container"`.
- Managed mount root validation remains mandatory for container input/output paths.
- Local synthetic tests explicitly pass `path_kind="host"`; this skips only the managed-mount root check. Final input still uses InputManager no-follow/descriptor/size verification, and final SAFE publication still uses OutputManager create-only atomic writing.
- Symlinked final input files remain rejected.

Latest GitHub validation at this commit:
- R60 HF Runtime CI Run `41808603414`: SUCCESS; Ruff, Compile, Runtime, Volume, Skill and R59 adapter tests all passed.
- Repository CI Run `41808603086`: SUCCESS; tests and Evidence Integrity passed.
- CPU tokenizer dependency lock Run `41808603081`: SUCCESS.
- R58 scoped synthetic Run `41808603506`: FAILURE at its existing Environment and scoped test baselines step; remains separately held and must not be treated as an R60 regression without inspecting that job's log.

Owner must pull this fix and rerun the local commands. Real R59 Pilot8 CPU Tokenizer Job remains NOT RUN until that local rerun passes.
