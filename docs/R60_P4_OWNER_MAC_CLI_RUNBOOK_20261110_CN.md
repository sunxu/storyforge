# StoryForge R60 P4 Owner Mac CLI Runbook（2026-11-10）

> 目的：Owner 在 Mac 上复核固定 amd64 镜像的 CLI fail-closed 行为。此流程仅 CPU-only、未授权 Profile、合成/空输入路径；不提交 HF Job、不测试 Bucket、不执行推理。
>
> 固定镜像：`docker.io/pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee`

## 1. 同步与核验分支

先确认本地没有未提交改动。若有改动，停止并自行决定如何处理；不要 reset、clean、stash 或覆盖工作区。

```bash
cd /Users/keedle/workspace/storyforge-r60-ledger-diagnostics
git status --short --branch
git fetch origin
git switch r60/p4-generation-eval-framework
git pull --ff-only origin r60/p4-generation-eval-framework
git rev-parse HEAD
git status --short --branch
```

将 `git rev-parse HEAD` 与 PR #30 当前 head SHA 对照。必须在执行前从 GitHub 重新读取 PR #30 的最新 head SHA；不使用本 Runbook 创建时的历史 SHA。

## 2. 拉取并检查固定镜像

```bash
IMAGE='docker.io/pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee'

docker pull --platform linux/amd64 "$IMAGE"

docker image inspect "$IMAGE" \
  --format '{{.Os}}/{{.Architecture}} {{.Id}}'
```

必须为 `linux/amd64` 且 image ID 与 digest 对应。Apple Silicon 需要 Docker/OrbStack amd64 仿真；如果容器无法启动或平台不匹配，停止并记录，不得换成未固定的 ARM 镜像冒充通过。

## 3. CPU-only CLI 参数与 fail-closed 自检

```bash
set -euo pipefail
IMAGE='docker.io/pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee'
ROOT="$PWD"

docker run --rm --platform linux/amd64 --network none \
  -v "$ROOT:/workspace/storyforge:ro" \
  -e PYTHONPATH=/workspace/storyforge/src \
  -e STORYFORGE_RUNTIME_IMAGE_DIGEST='sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee' \
  --entrypoint bash "$IMAGE" -lc '
    set -euo pipefail
    python -m storyforge_dataset.generation_eval.worker_cli --help | grep -- --model-role
    mkdir -p /output
    set +e
    report=$(python -m storyforge_dataset.generation_eval.worker_cli \
      --model-role A \
      --profile /workspace/storyforge/experiments/r60_quality/p4_generation_profile_candidate_v1.json \
      --manifest /input/manifest.json \
      --input /input/inputs.jsonl \
      --output-dir /output/owner-cli-selftest \
      --repo-root /workspace/storyforge 2>&1)
    code=$?
    set -e
    printf "%s\\n" "$report"
    test "$code" -eq 2
    printf "%s" "$report" | grep -q GENERATION_PROFILE_NOT_AUTHORIZED
    test ! -e /output/owner-cli-selftest
    echo "OWNER_MAC_CPU_FAIL_CLOSED_SELFTEST_PASS"
  '
```

预期：`--help` 能列出 CLI 参数；正式入口返回 exit code 2 和 `GENERATION_PROFILE_NOT_AUTHORIZED`；没有创建输出目录。由于容器 `--network none` 且候选 Profile 的三个生产授权字段均为 false，不会下载 tokenizer/权重，不会调用模型，不会启动 GPU 或训练。

该流程不能证明授权 Profile 下的真实生成能力，也不测试 HF 输出卷。不能通过临时修改 Profile 授权字段来绕过这一边界。

## 4. Owner SAFE 回传要求

只回传：
- 命令退出码；
- 镜像平台和 digest；
- SAFE JSON（仅聚合状态）；
- 是否创建输出目录；
- 是否发生 GPU / inference / training（预期均 false）。

不要回传私有输入、生成正文、token、PAT、DSN 或其他凭据。

## 5. HF Job 的边界

本 Runbook 不包含 `hf jobs run`。后续任何 HF Job 只有在 Owner 独立批准对应阶段、数据范围、GPU flavor、硬超时与费用上限后，才由 Owner 自行从 Mac CLI 执行。ChatGPT/Agent 不提交 Job、不探测 Bucket、不修改 OAuth 或 ACL。
