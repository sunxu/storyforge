# StoryForge R53 — Hugging Face CPU 40 条真实输入验收

**状态：本文件为部署准备，不代表 Job 已启动、40/40 已 PASS 或训练数据已正式准入。**

## 约定与依据

沿用 [R18](V02_R18_NO_TRAIN_HF_RUN.md)、[R27](evidence/V02_R27_HF117_COMPLETED_OWNER_LOG_20261013.md) 的 Hugging Face CPU 工作流：Mac 操作 `hf` CLI；私有数据存 `hf://buckets/adradar/storyforge-training`；`cpu-upgrade` 付费 Job 运行固定 Qwen tokenizer、ms-swift 和真实 Collator；结果保存在私有 Bucket。R50 不读取，无 `swift sft`，没有 GPU。

完整固定源：

| 输入 | 行数 | SHA256 |
|---|---:|---|
| `STAGED_TRAIN_NOT_ADMITTED.jsonl` | 31 | `f17fc33f566b5a1ddd424de2d26a032a812453255c76e0f5fa321fb0f3a9ecf9` |
| `STAGED_VALIDATION_NOT_ADMITTED.jsonl` | 9 | `83e3d1ab4cc955c4b5bba2afc63f355a227934a89203bcc058cfb922a093b01d` |
| `STAGED_31_9_SOURCE_HASH_MANIFEST_PRIVATE.json` | — | `00b8182812d8bbc33eaacede962506ec718c6b987ef82c429f75401c4c107261` |

固定版本：`Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`、`ms-swift==4.5.3`、`transformers==5.16.1`、仓库官方 `scripts/hf_label_mask_audit.py` 的 Git blob SHA-1 `15296f1d8438f40d727c84913ac658cf6de01cb4`。

## 1. Mac 端准备，不启动 Job

此版本交付包内包含实际实现脚本。先将**代码文件**复制到本地 Git checkout 的 `scripts/`，而将**私有正文数据**保存到项目仓库外：

```bash
cd ~/workspace/storyforge
git switch main
git pull --ff-only origin main
HF_CPU_HANDOFF="$HOME/.local/share/storyforge/r53-hf-cpu40-handoff"
mkdir -p "$HF_CPU_HANDOFF"
unzip -n "$HOME/Downloads/StoryForge_R53_HF_CPU40_SYNC_SUBMIT_VERIFY_PRIVATE_20261021.zip" \
  -d "$HF_CPU_HANDOFF"
cp "$HF_CPU_HANDOFF/scripts/"v03_r53_hf_cpu40_*.py scripts/
cp "$HF_CPU_HANDOFF/scripts/"v03_r53_hf_cpu40_*.sh scripts/
# 仓库原有 scripts/hf_label_mask_audit.py 必须保持不变。
hf auth whoami
```

请在 GitHub 归档以上**非私有代码**。GitHub 提交不包含 `private_stage/`、Job 返回的私有日志或逐条身份。

当前 R53 HF CPU40 交付包已经包含**原封不动的** `private_stage/`。将其从交付解压目录拷贝到你的私有工作目录，不要提交到 GitHub：

```bash
mkdir -p "$HOME/.local/share/storyforge/r53"
cp -R "$HF_CPU_HANDOFF/private_stage" "$HOME/.local/share/storyforge/r53/"
STAGE="$HOME/.local/share/storyforge/r53/private_stage"
python3 scripts/v03_r53_hf_cpu40_audit.py preflight --stage "$STAGE"
```

`R53_STAGE_PREFLIGHT_PASS 31/9` 表示**静态来源门禁**，不是 ms-swift 的真实运行时 PASS。

## 2. `sync`：只上传私有输入与代码，不创建 CPU Job

```bash
bash scripts/v03_r53_hf_cpu40_submit.sh sync "$STAGE"
```

成功时会输出唯一 `R53_RUN_KEY=r53-cpu40-...` 和对应的私有 Bucket 运行前缀。**保存它**。每次 sync 使用一个新的运行键，远程代码和数据会有 SHA256 清单；不要手工复用旧键。sync 可能发生存储/传输费用，但不启动计算 Job。

## 3. `submit`：需要你另行明确授权付费 CPU 才可执行

只有你确认接受这次 **单独的付费 CPU Job** 后，才执行：

```bash
RUN_KEY='r53-cpu40-...这里填 sync 打印的实际值...'
STORYFORGE_ALLOW_PAID_CPU=YES \
STORYFORGE_R53_CPU40_NO_TRAIN_ONLY=YES \
bash scripts/v03_r53_hf_cpu40_submit.sh submit "$RUN_KEY"
```

提交器使用既有项目规范：`hf jobs run --namespace adradar --flavor cpu-upgrade --timeout 120m`、只读原始文本与脚本、私有 Bucket `/workspace` 挂载和 `pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime` 镜像。镜像名称带 CUDA 仅用于沿用历史已测试依赖环境；Job Flavor 是 **CPU**，Worker 明确设置 `CUDA_VISIBLE_DEVICES=""`，不做模型加载/训练。

Worker **先执行包 SHA256、31/9 原文/消息哈希和只监督最终 Assistant 的静态门禁，再 pip install**。通过后只下载 Qwen 固定 revision 的 tokenizer/config/chat-template 等小文件，不下载模型权重。

> `120m` 是最大允许运行时限而非预计耗时。**这个 Job 是计费资源**，必须单独批准。当前无自动定时提交、无重试风暴。若失败，检查日志而非自动重跑。

## 4. 获取真实 Job 日志和结果

记录 `hf jobs run` 实际打印的 JOB_ID：

```bash
hf jobs logs -f adradar/JOB_ID
RUN_KEY='r53-cpu40-...实际键...'
PREFIX="hf://buckets/adradar/storyforge-training/preflight/v03-r53/cpu40"
D="$HOME/.local/share/storyforge/r53/results/$RUN_KEY"
mkdir -p "$D"

hf buckets cp "$PREFIX/results/$RUN_KEY/audit/R53_HF_CPU40_AUDIT_REPORT_PRIVATE.json" \
  "$D/R53_HF_CPU40_AUDIT_REPORT_PRIVATE.json"
hf buckets cp "$PREFIX/results/$RUN_KEY/R53_CPU40_RUNTIME_LOG_PRIVATE.txt" \
  "$D/R53_CPU40_RUNTIME_LOG_PRIVATE.txt"
hf buckets cp "$PREFIX/results/$RUN_KEY/R53_CPU40_RUNTIME_LOG_SHA256SUMS.txt" \
  "$D/R53_CPU40_RUNTIME_LOG_SHA256SUMS.txt"
```

**注意：以上命令中的 JOB_ID、RUN_KEY 都必须填实际的值，不可照抄占位符。** Job 日志在失败时可能包含原文附近 token 的调试片段，必须私有保存。

## 5. 取回后在 Mac 做标准库回执验收（无需本地 transformers）

```bash
python3 scripts/v03_r53_hf_cpu40_verify.py \
  --stage "$STAGE" \
  --report "$D/R53_HF_CPU40_AUDIT_REPORT_PRIVATE.json" \
  --runtime-log "$D/R53_CPU40_RUNTIME_LOG_PRIVATE.txt" \
  --out "$D/R53_HF_CPU40_LOCAL_VERIFICATION.json"
```

成功的 HF 结果需具有实际 40/40 `R53_ACTUAL_HF_CPU40_LABEL_MASK_PASS 40/40` 运行日志标记、40 条正确身份哈希、Qwen revision/tokenizer 文件哈希、`ms-swift==4.5.3`、`transformers==5.16.1`、最后回复标签及 Collator 一致性。此命令不运行真实模型，只验收远程报告与冻结数据。

上传给 ChatGPT 时建议上传 **CPU Job ID、上述 JSON 回执及脱敏状态回执**。原始日志可能包含你的私有故事片段，不要公开提交。验收通过后仍须满足来源权利政策及**独立训练数据发布批准**，绝不自行启动 GPU。

## 当前状态

- 源数据：**已静态验证 31/9，不变**。
- 真实 `ms-swift` + `transformers` + `data_collator`：**尚未在本轮 CPU Job 执行**。
- 正式 Train/Val：**0/0**，私有暂存不代表训练获批。
- 历史 R46 输入：用户上传的本机真实导出核验回执已通过交叉检查。
- R50 密封，不读取；GPU 无授权。