# R58 Gold195 — HF GPU 双模型独立盲审操作手册

日期：2026-11-01。状态：代码与合成测试通过；未提交真实付费 GPU 评审。

## 不变约束

- A: Qwen/Qwen3-32B，H200；B: zai-org/GLM-4-32B-0414，H200。GLM 已被 vLLM 0.11.0 列为支持，但本轮真实加载未测。
- A/B 各只读自己的 13 条盲审输入，Owner crosswalk 仅保存在 Mac，不上送 GPU。
- 先 A 2 条 + B 2 条；通过结构、原文引用及 PRIVATE 结果回收后，才可运行剩余 11+11。
- 卡片仅是待审来源快照，不是原生产 System；模型 PASS 不等于可信世界卡或 Quality-v1 正式准入。
- 无隐式 GPU 提交；成本需用户单独批准。任何失败保持 HOLD，禁止伪造质量分数。
- Hugging Face 本地目录挂载会同步至账号 PRIVATE jobs-artifacts Bucket，RW 结果必须依据 CLI 提供的真实 hf buckets sync 命令拉回；Job 成功状态不能代替文件落盘验证。

## 1. Mac 本地隔离分发

进入 StoryForge 的 r58/roleplay-sft-skill-v01 分支，运行以下 Shell 命令。
把 RUN_DIR 中 YYYYMMDDTHHMMSSZ 换成之前成功生成的真实时间戳。
STAGE 必须是一个此前不存在的新私人目录。

    git switch r58/roleplay-sft-skill-v01
    git pull --ff-only
    umask 077
    RUN_DIR="$HOME/.local/share/storyforge/r58/r58-quality-pilot13-YYYYMMDDTHHMMSSZ"
    STAGE="$HOME/.local/share/storyforge/r58/r58-hf-gpu-dual-review-stage-v1"
    python3 experiments/r58_quality/r58_hf_gpu_review_stage.py \
      --pilot-dir "$RUN_DIR" --stage-dir "$STAGE" --repo-root "$PWD"

期望 R58_A_B_PRIVATE_GPU_STAGING_READY__NOT_SUBMITTED。目录如下：

- STAGE/input_A/source.private.jsonl 和 runner.py；STAGE/output_A 初始为空
- STAGE/input_B/source.private.jsonl 和 runner.py；STAGE/output_B 初始为空

不要上传 RUN_DIR/owner_crosswalk.private.json。

## 2. 模型 Revision 钉死

    QWEN_SHA="9216db5781bf21249d130ec9da846c4624c16137"
    GLM_SHA="$(python3 -c 'from huggingface_hub import HfApi; print(HfApi().model_info("zai-org/GLM-4-32B-0414").sha)')"
    [[ "$GLM_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo GLM_REVISION_HOLD; exit 42; }

GLM 需要 Mac Python 安装 huggingface_hub；不能传 main 代替固定 SHA。GLM revision 属于该次校准的绑定信息，后续必须复用。

## 3. 使用廉价 CPU 检查本地目录 RW 挂载权限

需要 Owner 同意支付 CPU Job 成本后，执行：

    hf jobs run --namespace adradar --flavor cpu-basic --timeout 3m \
      -v "$STAGE/input_A:/input" -v "$STAGE/output_A:/output:rw" \
      python:3.12 -- python -c \
      'from pathlib import Path; assert Path("/input/source.private.jsonl").is_file(); Path("/output/r58_rw_probe.txt").write_text("HF RW OK"); print("R58_PRIVATE_VOLUME_RW_SMOKE_PASS")'

CLI 会显示对应的 HF 私有 Bucket sync 命令。Job 完成后按其输出的真实命令拉回 Mac，确认 STAGE/output_A/r58_rw_probe.txt 存在。随后还应对 B 使用相同方法测试其独立输出路径。任何 403 或回收失败立即 HOLD，不进入 GPU。

这里使用本地目录挂载，不是直接使用此前失败的 adradar/storyforge-training:rw 挂载。即使如此，权限是否可用也必须以现场测试为准。

## 4. 先执行 A 的 2 条 H200 试点（需要明确 GPU 预算授权）

    hf jobs run --namespace adradar --flavor h200 --timeout 45m \
      -v "$STAGE/input_A:/input" -v "$STAGE/output_A:/output:rw" \
      vllm/vllm-openai:v0.11.0 -- python3 /input/runner.py \
      --slot A --model Qwen/Qwen3-32B --revision "$QWEN_SHA" \
      --input /input/source.private.jsonl --output-dir /output \
      --phase pilot --max-model-len 32768 --max-output-tokens 2400

通过后再独立执行 B 的 2 条：

    hf jobs run --namespace adradar --flavor h200 --timeout 45m \
      -v "$STAGE/input_B:/input" -v "$STAGE/output_B:/output:rw" \
      vllm/vllm-openai:v0.11.0 -- python3 /input/runner.py \
      --slot B --model zai-org/GLM-4-32B-0414 --revision "$GLM_SHA" \
      --input /input/source.private.jsonl --output-dir /output \
      --phase pilot --max-model-len 32768 --max-output-tokens 2400

建议两次按顺序执行以限制账单。两个 Job 都需返回 R58_HF_GPU_REVIEW_PILOT_VALID，且各自通过 CLI 显示的 sync-back 命令把 checkpoint_00.private.json / checkpoint_01.private.json 回收到原 STAGE/output_A/B 目录。任何引用不精确、Token 超限、JSON 格式失败均 HOLD，不补写虚假结果。

## 5. 剩余 11+11（另行批准、独立提交）

保持同一套 INPUT/OUTPUT、模型 SHA、上下文和输出预算，把对应命令的 --phase pilot 改为 --phase remaining。必须首先读取、核验已有前两条私有检查点；缺少或变化则立即 HOLD。正常完成后分别形成 reviewer_A.completed.private.jsonl 和 reviewer_B.completed.private.jsonl。每次 Job 后回收 RW Bucket 的持久结果，验证 13 条完整性，不要覆盖原始盲审材料。

## 6. Owner 双审验收

    python3 experiments/r58_quality/r58_gold195_pilot13_dual_review_validate.py \
      --reviewer-a-source "$RUN_DIR/reviewer_A.private.jsonl" \
      --reviewer-a-completed "$STAGE/output_A/reviewer_A.completed.private.jsonl" \
      --reviewer-b-source "$RUN_DIR/reviewer_B.private.jsonl" \
      --reviewer-b-completed "$STAGE/output_B/reviewer_B.completed.private.jsonl" \
      --owner-crosswalk "$RUN_DIR/owner_crosswalk.private.json"

此验收只认证数据形状、来源字节稳定、双模型审核结果及逐字引用，仍输出 quality_v1_admitted=0、training_authorized=false。下一步才是文学争议仲裁、可信卡片判断、世界级 Train/Val/R50 隔离和正式冻结。

## 状态

已实现：A/B 安全分发、vLLM JSON schema、固定模型 revision 合同、原文引用核验、2+11 阶段、检查点恢复与训练禁入。
尚未完成：Mac PRIVATE 数据分发、HF 本地 RW 回收测试、任何本次真实付费 GPU 推理。 
