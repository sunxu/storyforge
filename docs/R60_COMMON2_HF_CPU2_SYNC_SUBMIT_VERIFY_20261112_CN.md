# StoryForge R60 — Common2 两条实验性SFT：复用R53 HF CPU真实Collator验收

2026-11-12。Owner明确：**不在Mac安装ms-swift或完整训练栈**；使用曾在R53/R27/R18中验证的HF CPU no-training流程。此处只准备脚本与Owner Mac指令，**当前未同步私有数据、未创建付费CPU Job，也未启动GPU**。

## 当前真实事实与边界

- 独立质量PASS2、103/243条持久化源历史已恢复，采用最近11条历史构造2条实验性SFT输入；原始实际发送System/世界卡并未验证。
- Owner已在Mac使用固定Qwen tokenizer revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` 对两条真实实验样本得到 **2552、4048** tokens；上限16384。
- Mac直接运行现有`--stage both`得到`COMMON2_CPU_TEMPLATE_AUDIT_HOLD`；此通用状态无法证明是输入问题，且**历史项目从未要求Mac安装完整ms-swift**。
- Wave40先前选好的40位置仍私有冻结、暂停盲审；完整R50隔离仍HOLD，`train_admitted=0`。

## 可复用程序

- `scripts/r60_common2_hf_cpu_stage.py`：Mac纯标准库，检查私有输入源文件权限及sha、2/2数据合同、目标仅最后assistant、训练准入0；递归收集实际脚本所依赖的本仓库Python模块，并强制官方`hf_label_mask_audit.py` Git blob保持`15296f1d8438f40d727c84913ac658cf6de01cb4`。构造**不覆盖**的0700私有stage文件夹及SHA256SUMS；没有外部调用。
- `scripts/r60_common2_hf_cpu_bucket_guard.py`：复用R53 read-only `HfApi.list_bucket_tree`，**确认远程新运行键不存在、同步后文件集合与本地manifest完全一致**；鉴权错误即拒绝，不能把空`hf buckets ls`返回码当作成功证据。
- `scripts/r60_common2_hf_cpu_submit.sh`：`sync`仅上传数据/代码与最后的hash清单，不启动Job；`submit`需要`STORYFORGE_ALLOW_PAID_CPU=YES`与`STORYFORGE_R60_COMMON2_NO_TRAIN_ONLY=YES`双重明确授权，同时重复核对Bucket文件集合。
- `scripts/r60_common2_hf_cpu_worker.sh`：仅`cpu-upgrade` Flavor、`CUDA_VISIBLE_DEVICES=\"\"`，先验证所有stage SHA256，再按R53成功依赖安装`ms-swift==4.5.3`、`transformers==5.16.1`，仅下载冻结Qwen tokenizer/config/模板**不下载模型权重**；将只读私有源复制到HF Job专属0700/0600目录，调用已有`r60_common2_sft_cpu_template_audit.py --stage both`，继续使用R18/R53真实`hf_label_mask_audit.py`检查`last_round`、最终Assistant-only Loss、真实Collator后标签。**不执行`swift sft`或任何训练**。仅向Bucket保存SAFE JSON和运行状态，不公开私有正文。

## Mac：先完成离线测试，再选择同步

使用已固定版本Owner工作树，不强制切换本地已被其他worktree占用的分支：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
git status -sb
python3 -m pytest -q tests/test_r60_common2_hf_cpu_stage.py

BASE="$HOME/.local/share/storyforge/r60/private"
INPUT_DIR="$BASE/r60-real1000-common2-sft-experimental11-v1"
test -f "$INPUT_DIR/R60_COMMON2_SFT_EXPERIMENTAL_MANIFEST_PRIVATE.json"
test -f "$INPUT_DIR/R60_COMMON2_SFT_EXPERIMENTAL_NOT_ADMITTED_PRIVATE.jsonl"
```

**这一步零远程调用；脚本本身不依赖Mac Transformers、Swift或Torch。**

### 1. `sync`：只同步私有Bucket，不创建任何Job

先通过Owner账户`hf auth whoami`确认权限。仅在Owner明确接受**将当前两条私有互动小说正文上传至现有受限Bucket**的情况下执行：

```bash
bash scripts/r60_common2_hf_cpu_submit.sh sync "$INPUT_DIR"
```

输出示例只包含新键与本地stage路径：

```text
R60_COMMON2_RUN_KEY=r60-common2-cpu2-...-...
R60_COMMON2_PRIVATE_STAGE_DIR=/Users/.../.local/share/storyforge/r60/hf-cpu2-stages/<RUN_KEY>
R60_COMMON2_SYNC_READY__NO_JOB
```

保存实际RUN_KEY和STAGE_DIR。**不要使用示例占位符作为真实运行键**。同步可能产生网络/存储费用，但不会启动计费计算。

### 2. `submit`：单独明确付费CPU批准后才执行

`cpu-upgrade`可能收费。只有Owner另行授权**这一次特定运行键**才使用下列命令：

```bash
RUN_KEY="前一步真实打印的键"
STAGE_DIR="前一步真实打印的本地stage目录"

STORYFORGE_ALLOW_PAID_CPU=YES \
STORYFORGE_R60_COMMON2_NO_TRAIN_ONLY=YES \
bash scripts/r60_common2_hf_cpu_submit.sh submit "$RUN_KEY" "$STAGE_DIR"
```

此操作运行**单次**HF Job（`--flavor cpu-upgrade --timeout 120m`），属于计费资源；没有自动重试、没有GPU，超时是硬上限不是预计运行时长。

HF CLI会打印JOB_ID，保存后查看日志：`hf jobs logs -f adradar/JOB_ID`（必须以真实ID代替）。

### 3. 仅拉回SAFE验收回执

仅在Worker成功结束后：

```bash
RUN_KEY="真实运行键"
BASE="$HOME/.local/share/storyforge/r60/private"
D="$BASE/r60-common2-hf-cpu2-result-$RUN_KEY"
mkdir -m 700 "$D"
hf buckets cp \
 "hf://buckets/adradar/storyforge-training/preflight/r60/common2/cpu2/results/$RUN_KEY/R60_COMMON2_CPU2_SAFE_RECEIPT.json" \
 "$D/R60_COMMON2_CPU2_SAFE_RECEIPT.json"
chmod 600 "$D/R60_COMMON2_CPU2_SAFE_RECEIPT.json"
cat "$D/R60_COMMON2_CPU2_SAFE_RECEIPT.json"
```

目标严格为`COMMON2_CPU_TOKENIZER_COLLATOR_PASS__R50_TRAIN_HOLD`，须有`cases=2`、`collator_verified=true`、`r50_complete_exclusion_verified=false`、`train_admitted=0`。失败时不能改变窗口、覆盖冻结文件或自动重新计费；需先按SAFE阶段信息定位CPU-only错误。

## 后续真正门禁

远程Collator成功仅意味着**技术格式通过**，不是准许SFT。继续完成**完整R50受保护故事、会话、消息源隔离**（五个已知故事不足以替代全量）；确认世界/角色信息不足问题；之后再由Owner另行决定是否准入和是否启动GPU。**Wave40保留待审，但不是此次验收的一部分。**
