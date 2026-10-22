# StoryForge R50 — 46 题 HF CPU Tokenizer (DRAFT) 安全执行包

**交付状态：本包代码已进行合成单元测试，但未连接用户 HF、未上传 R50 原文、未启动云端 Job、未真实读取 R50 题文、未获得正式测试准入。**

## 任务用途与不变量

沿用 StoryForge R53/R54 已运行的 `sync → submit → verify` 规范：

- **Mac 仅要求已安装的 `hf` CLI、Python 3 标准库、Git、Bash**。不要在 Mac 安装 Transformers、ms-swift、Torch 或下载模型权重。
- **远端仅使用 CPU flavor `cpu-upgrade`**，`python:3.12-slim` 中在输入 SHA256 核验后 `pip install transformers==5.16.1, huggingface_hub, jinja2`。不加载模型权重、不训练、不生成回复、不触碰 R50 答案。
- 原始 R50 冻结 50 题保持不变，本任务仅对明确排除四题后的 46 题 **PRESEAL** 文件执行 **Option A DRAFT** Tokenizer 预检。`thinking disabled`、`max_context=16384`、`reserved_output=1536` 均未获正式合同批准。
- **不会上传至** `hf://buckets/adradar/storyforge-training`；也**不使用**先前自动 `greenkeedle/jobs-artifacts`。使用 **adradar 组织下单独的私有审核 Bucket** `hf://buckets/adradar/storyforge-r50-audit`，除非你明确修改参数且确保相同隔离安全性。
- 每次运行唯一 `RUN_KEY`，所有脚本/输入按 SHA256 固定，`SHA256SUMS.txt` 最后上传，提交 Job 前从 HF 逐个下载回读精确对比。
- `submit` 默认拒绝。只有运行时同时设 `STORYFORGE_ALLOW_PAID_CPU=YES`、`STORYFORGE_R50_CPU46_DRAFT_ONLY=YES` 才允许单次收费 CPU Job。**失败不自动重试**。
- Mac `verify` 下载实际报告和回执，对照 46 题原始 SHA、System 草案 SHA、原始审核脚本 SHA、阶段清单和 Job 输出文件 SHA。不会凭 Job 名称或单条日志输出报 PASS。
- **语义世界关联、12 个连续 User 输入的最终拼接规则、46 题 Token 上限、四模型一致合同与正式封存均仍 HOLD**。本包的 `SUCCESS` 只表示官方运行脚本正常退出、报告为可解析 JSON、并可回验远端文件哈希；实际 Token 长度仍需后续读取报告的安全统计结果。

## 0. 下载与安装脚本（本地代码，不要将私有题文放进 Git）

下载 `StoryForge_R50_HF_CPU46_GitFirst_20261022.zip` 到 `~/Downloads`。建议解压到已有 StoryForge Git 仓库**以外**，例如：

```bash
BUNDLE="$HOME/.local/share/storyforge/r50/hf-cpu46-tools-v2"
mkdir -p "$BUNDLE"
unzip -n "$HOME/Downloads/StoryForge_R50_HF_CPU46_GitFirst_20261022.zip" -d "$BUNDLE"
# 注意：ZIP 根目录即含 scripts/、tests/、docs/
python3 -m unittest discover -s "$BUNDLE/tests" -v
```

如需 Git-first 归档，可以仅把 `scripts/`、`tests/`、`docs/` 中**不含剧情/题目正文**的代码及说明作为版本化提交；不要提交本机 `RUN_KEY/stage/private`、Job 日志或 Tokenizer 原始题文报告。

## 1. 首次执行前，单独创建私人 R50 Bucket

这个命令由 Owner 明确运行，之后无需重复创建：

```bash
hf auth whoami
hf buckets create adradar/storyforge-r50-audit --private
hf buckets info adradar/storyforge-r50-audit
```

`info` 必须显示 `"private": true`。**即使个人 `jobs-artifacts` 已有文件，也不要与本 Bucket 混用。** 确认 Bucket 访问权限符合你对 R50 独立测试的保密要求：HF 组织管理员与有 Bucket 读取权限的成员仍可能读取明文；同属 `adradar` 不等于已经完成访问隔离，请在同步前确认可访问人员名单。对于无法隔离的访问控制，请不要上传 R50。

## 2. 本机准备 R50 私有文件

原本已经存在的三个私有原始文件需要能在 `$HOME/.local/share/storyforge/r50` 或 `~/Downloads` 下找到（可递归）：

- `R50_CANDIDATE_46_PRESEAL_PRIVATE.jsonl`，固定 SHA256 `109642a6c0e27895ae83274bec79ec9f53d922e407ca435431acf3f31a31e1f2`。
- `R45_SYSTEM_CANDIDATE_64_OF_64_NOT_APPROVED_PRIVATE.txt`，固定 SHA256 `5e1b28cd9181f5d334f1f10a54a251f9255e655a3e597519c7cfcc530d8c5e83`。
- `R50_CPU_TOKENIZER_PREFLIGHT_46.py`，使用你之前收到的原有**私有脚本**，不生成替身脚本（其 SHA256 在本次运行阶段单独记录）。

如在其他目录，可手工显式设路径：

```bash
export R50_CASES='/private/actual/path/R50_CANDIDATE_46_PRESEAL_PRIVATE.jsonl'
export R50_SYSTEM='/private/actual/path/R45_SYSTEM_CANDIDATE_64_OF_64_NOT_APPROVED_PRIVATE.txt'
export R50_PREFLIGHT='/private/actual/path/R50_CPU_TOKENIZER_PREFLIGHT_46.py'
```

不要让 CI、一般模型研发人员或公开 Git 仓库看到上述内容。

## 3. `sync`：只上传到私有 Bucket，不提交 CPU Job

```bash
BUNDLE="$HOME/.local/share/storyforge/r50/hf-cpu46-tools-v2"
bash "$BUNDLE/scripts/v03_r50_hf_cpu46_submit.sh" sync
```

成功后打印：

```text
R50_CPU46_STAGE_LOCAL_SHA256_PASS__NO_JOB
R50_REMOTE_STAGE_6_OF_6_BYTES_MATCH__NO_JOB
R50_RUN_KEY=r50-cpu46-....
R50_SYNC_READY__NO_HF_JOB=hf://buckets/adradar/storyforge-r50-audit/preflight/r50/cpu46/runs/.../
R50_NO_PAID_CPU_JOB_EXECUTED
```

私有分阶段资料只在 Bucket 与 Mac 的 `~/.local/share/storyforge/r50/hf-cpu46/<RUN_KEY>/stage/`。如路径不符、SHA 不符、Bucket 非 private、远端对象不一致，**直接 HOLD**，不要继续。

## 4. `submit`：明确认可一次性收费 CPU 才运行

运行前请自行确认 HF 账户计算余额/费用上限。`cpu-upgrade`/`90m` 为 flavor 与**超时上限**，不代表实际运行时长。用户可自行调整源码配置，但应重新审计后再 sync 新 RUN_KEY。

```bash
RUN_KEY='r50-cpu46-...复制上一步实际输出...'
STORYFORGE_ALLOW_PAID_CPU=YES \
STORYFORGE_R50_CPU46_DRAFT_ONLY=YES \
bash "$BUNDLE/scripts/v03_r50_hf_cpu46_submit.sh" submit "$RUN_KEY"
```

Worker 在远端依次：验证完整阶段清单与 46 条真实输入 → 安装依赖 → 下载固定 Qwen revision 的少量 Tokenizer 相关文件 → 执行原有 `R50_CPU_TOKENIZER_PREFLIGHT_46.py` → 保存私有报告与脱敏回执。

**不应把 `R50_HF_CPU46_TOKENIZER_SCRIPT_COMPLETED__DRAFT_NOT_ADMITTED` 解释为 46 题全部正式长度通过**。其业务字段由下一轮审计核查。

若 CLI 超时或提交错误但无法证明创建失败，**不要重复 submit 同一 RUN_KEY**。先查看：

```bash
hf jobs ls -a --namespace adradar
# 用结果里的实际 ID，而非占位符
hf jobs logs JOB_ID
```

## 5. `verify`：Mac 标准库验收，无 Transformers

远端完成后执行：

```bash
bash "$BUNDLE/scripts/v03_r50_hf_cpu46_submit.sh" verify "$RUN_KEY"
```

验收成果存放在：

```text
~/.local/share/storyforge/r50/hf-cpu46/<RUN_KEY>/results/
  R50_CPU46_OWNER_INTAKE_COUNT_ONLY.json      <-- 可以分享的脱敏回执
  R50_CPU46_COUNT_ONLY_RECEIPT.json          <-- 远端脱敏技术回执
  R50_46_CPU_TOKENIZER_DRAFT_PRIVATE.json    <-- 私有逐题报告，勿直接贴到 Git
  R50_CPU46_PREFLIGHT_OUTPUT_PRIVATE.txt     <-- 原始脚本日志可能含私有片段
```

请优先分享 `R50_CPU46_OWNER_INTAKE_COUNT_ONLY.json` 和终端状态标记，不要分享私有报告或日志原文。对于不一致/没有报告的任务，标记 HOLD，不能声称真实 Qwen 检查 PASS。

## 6. 安全限制、后续实际审核

- R50 五个故事源 16–20 与 R45 的**精确窗口** Mac 检查已经由 Owner 报告通过，**语义关联 HOLD** 仍有效。
- HF `jobs-artifacts` 未用于本新任务；原来是否有中途上传/缓存需要通过个人账户检查，**不能推定已删除或仍存在**。
- Bucket 是持久对象存储，**本流程不会自动删除**远端副本。请在取得验收回执、符合你的保管策略后单独决定清理。
- 私有 Bucket 与 `hf jobs run` 产生的是 HF 供应商环境中的 R50 明文副本；如果你需要让训练/模型研发人员**完全不可访问**，必须检查 Bucket 权限/组织访问控制，不能仅凭 `private` 字样断言达成。
- 未正式 `seal`，未启动 GPU，未生成测试模型回答，未修改原始 Gold195 或 R50 50 原件，R54 仍为 `NOT_PROMOTED`。

历史依据（StoryForge GitHub）：`docs/V03_R53_HF_CPU40_SUBMIT_VERIFY_CN.md`、`scripts/v03_r53_hf_cpu40_submit.sh`、`scripts/v03_r53_hf_cpu40_worker.sh`、`scripts/v03_r53_hf_cpu40_verify.py` 及 `docs/V03_R54_HF_GPU_V2_SYNC_SUBMIT_VERIFY_CN.md`。
