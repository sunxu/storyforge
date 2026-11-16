# StoryForge R60 Base336：新Agent交接与立即执行指令（2026-11-16）

> **本文件是本轮快速探索性GPU训练的最近状态交接，优先于较早任务书中「再跑一次CPU336/293+43真实Collator」的步骤。** CPU旧证明只有通过原始行字节多重集合及历史HF回执双重严格核验后才可转移，不可根据旧CPU336口头PASS直接跳步。本文件不构成自动提交HF GPU的授权。

## 一、Owner决策与范围（不得擅自扩大）

- 本轮训练数据仅来源于既有冻结336候选：V1/V2/V3双PASS交集339减去3条已知R50重叠；**不能增加**R50、Gold72、P2B、旧R45或任何外部训练数据。
- 已冻结可用发布包：293 Train（146 Story）+43 Validation（26 Story）=336条；已知8组跨旧分组World JSON关联在新Train/Val之间均为0，不能等同于语义世界隔离完全PASS。
- 训练目标是一次全新Qwen Base QLoRA**探索性**实验；`train_admitted=0`保留，实验结果不能宣称正式准入、独立测试PASS或模型晋升。旧Provider reviewer独立性与R50语义隔离均HOLD。
- 不重新文学评审336×2；不反复挖Gold72/P2B历史，不重新划分、不重新生成私有293/43、不修改冻结旧文件；避免复用写死31/9、16-step和旧SHA的R54 GPU脚本。

## 二、真实现状（必须准确继承）

已通过Owner Mac实际运行：
1. `BASE336_EXPLORATORY_SPLIT_CREATED__GPU_HOLD`，293/43、336总计、已知World跨组0；
2. `BASE336_EXPLORATORY_RELEASE_BYTES_VERIFIED__GPU_HOLD`，`manifest_verified=true`、`sha256_verified=true`，对现有真实发布包字节和格式完成独立验证。

**尚无Owner实测**`BASE336_EXPLORATORY_FINAL_COLLATOR_PROOF_TRANSFER_PASS__GPU_HOLD`的SAFE回执；该项就是**新Agent的第一项任务**。此时`actual_final_collator_verified=false`，GPU Stage未准备，GPU Job未提交。不得将GitHub CI合成单测PASS写成Mac真实转移PASS。

分支：`r60/common2-cpu2-owner`；Mac工作树：`~/workspace/storyforge-r60-4router-review`；仓库：`https://github.com/sunxu/storyforge`。严格尊重并行Agent的改动：先fetch/比较当前树与最新分支、避免覆盖他人提交、不大范围重构，commit后验证CI。

旧HF CPU336：Run key `r60-base-cpu336-20261114T165256Z-9e35795990aa`，Bucket `hf://buckets/adradar/storyforge-training`。之前的CPU336模型真实Tokenizer / ms-swift Collator / R18 last-assistant label审核PASS，但原输入为TECHNICAL_NOT_ADMITTED。

Mac已封存新发布包（不要再创建第二份）：
```text
$HOME/.local/share/storyforge/r60/private/
  r60-base336-exploratory-20261116T020325Z-4314ad84d5cc/
    train.jsonl
    validation.jsonl
    R60_BASE336_EXPLORATORY_MANIFEST_PRIVATE.json
```
要求目录0700，私有文件0600，始终只读原件；不在聊天、GitHub、CI、stdout输出小说正文、Story ID、私有目标文本、哈希明细或API密钥。

已验证实现：
- `experiments/r58_quality/r60_base336_exploratory_release_verify.py`：真实发布包行数/权限/JSONL SHA与Manifest验收（**Owner已经PASS，无需重复执行**）。
- `experiments/r58_quality/r60_base336_exploratory_collator_transfer.py`：严格验证旧336技术包原字节SHA、原HF CPU336 SAFE回执，和新293+43每行**原始字节SHA多重集合相同**；返回的`collator_executed_in_this_run=false`，不能冒称此轮重新跑了ms-swift。
- `scripts/r60_base_cpu336_hf_receipt_verify.py`：不可跳过的历史HF回执接受函数。
- CI [#43790711112](https://github.com/sunxu/storyforge/actions/runs/43790711112)：Ruff PASS，304项合成测试PASS。CI没有读Owner的私有数据，**不能代替下一步Mac验证**。

## 三、第一步：Mac实际CPU336证明转移（仅旧SAFE回执下载，无HF CPU Job）

请直接使用以下命令。只有技术包真实目录与以下`TECHNICAL`不同，才只修改该变量为已存在的旧技术包位置；不能重新拼装技术包冒充旧HF源。

```bash
set -euo pipefail
set +x
umask 077

cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner

PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
RELEASE="$BASE/r60-base336-exploratory-20261116T020325Z-4314ad84d5cc"
TECHNICAL="$BASE/r60-base-cpu336-hf-packet-v1"
RECEIPT_DIR="$(mktemp -d "$BASE/r60-base336-proof-XXXXXXXX")"
chmod 700 "$RECEIPT_DIR"
RECEIPT="$RECEIPT_DIR/R60_BASE_CPU336_HF_SAFE_RECEIPT.json"

hf buckets cp \
 "hf://buckets/adradar/storyforge-training/preflight/r60/base-start/cpu336/results/r60-base-cpu336-20261114T165256Z-9e35795990aa/R60_BASE_CPU336_HF_SAFE_RECEIPT.json" \
 "$RECEIPT"
chmod 600 "$RECEIPT"

"$PY" experiments/r58_quality/r60_base336_exploratory_collator_transfer.py \
  --release-dir "$RELEASE" \
  --technical-dir "$TECHNICAL" \
  --cpu336-receipt "$RECEIPT"
```

**成功验收必须同时满足：**
- `status=BASE336_EXPLORATORY_FINAL_COLLATOR_PROOF_TRANSFER_PASS__GPU_HOLD`
- `source_cpu_receipt_accepted=true`
- `all_final_rows_byte_identical_to_audited_rows=true`
- `actual_final_collator_verified=true`，同时`collator_executed_in_this_run=false`
- `train_rows=293`，`validation_rows=43`
- `formal_source_admission_verified=false`、`train_admitted=0`、`gpu_stage_prepared=false`、`gpu_started=false`

若HOLD，先核实是否指向**真实原版**CPU336技术目录、旧HF回执是否正确下载、行字节格式是否不同；只用新的SAFE固定故障码或本地保密检查定位。禁止绕过SHA、修改冻结JSONL或旧回执、自动重跑HF CPU、将HOLD转换为PASS。若实际JSONL行序列化不一致，即使内容等价也不应将现有字节级转移PASS；须明确报告后决定是否必须做一次新的实际Collator审计。

## 四、转移PASS后的下一阶段（由新Agent继续实现）

1. 只读取真实的转移SAFE结果与现有发布包Manifest，记录训练输入`THREE_PERSISTED_MESSAGES_NO_SYSTEM`，禁止偷偷加入虚构System/角色卡/世界卡；修改训练输入合同会使转移证据失效。
2. 复用`scripts/v03_r54_gpu_runner.py`和R54已验收参数**作为实现参考**，研发**独立的R60 Base336 GPU stage/worker/submit**。禁止直接运行旧R54 hardcoded 31/9、16步或SHA。必须在提交前校验当前293/43字节SHA、唯一Stage、完整文件清单和模型revision，严格create-only及私有Bucket前缀隔离。
3. 固定基座`Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`；NF4/4bit、BF16、LoRA rank=64 alpha=128 dropout=0.05、max_length=16384、loss_scale=last_round、1 Epoch；按照**293实际Train样本和真实batch/accumulation设置重新计算**训练step数、evaluation/save间隔，验收最终checkpoint及adapter reload。GPU A100 80GB，先校验依赖版本和HF镜像。
4. 开发阶段先合成单测、Ruff、GitHub CI，再在Mac上只读预检、创建私有Stage、执行HF Bucket sync、远端SHA/文件集ready与`hf jobs run --dry-run`，确保无既有job与提交锁。没有这些门禁PASS不得发送付费GPU任务。待GPU提交需确认当前Owner授权适用于此确定的Stage及运行规格；若需要新的授权，则向Owner说明具体Run而不是假称已启动。
5. 单次HF GPU调用需要`O_EXCL`提交marker、唯一`RUN_KEY`、失败不自动重试、不覆盖旧私有Stage或HF结果，回执只提供SAFE汇总。结果必须标`EXPLORATORY_*__NOT_PROMOTED`。
6. 旧R47/R48/R55已暴露20题可以做开发回归，R50未完成语义/曝光隔离前不能称最终独立测试；不要为了赶训练擅自把Gold72/P2B转为训练数据。

## 五、优先级与退出标准

**当前唯一P0**：拿到Mac真实`BASE336_EXPLORATORY_FINAL_COLLATOR_PROOF_TRANSFER_PASS__GPU_HOLD`，或拿到可复现、原因明确的HOLD，并安全地处理。**先完成P0再展开GPU实现**，不要并行重复做CPU worker、重构冻结数据，避免改坏现有技术证明。

P0 PASS后，交付R60独立GPU构建/校验/提交链路，附Ruff/pytest GitHub CI、Mac SAFE stage receipt、远端READY、dry-run；符合要求后再进入单次A100提交。若不能完成，明确阻塞点，不猜测PASS。

## 六、给新Agent的启动提示词

请阅读本文件和`docs/plans/R60_BASE336_FAST_GPU_EXPLORATORY_20261116_CN.md`，以及最新的`r60_base336_exploratory_collator_transfer.py`、`scripts/r60_base_cpu336_hf_receipt_verify.py`源代码。

你的**第一个实际任务**不是编写GPU训练器：先指导Owner在Mac执行本文件第三节的CPU336原证明转移。严格复核旧HF回执、旧336技术包、最终293/43行字节集合，一切真正PASS基于实际SAFE。不要重复跑HF CPU、不重做数据划分、不扩增训练样本。成功后继续实现独立R60 GPU Stage/Worker/CLI并在真实SHA、模型固定revision、GPU运行保护下准备A100 QLoRA探索性首训。保持`train_admitted=0`与`NOT_PROMOTED`、不更改正式六门禁、不把合成CI当实战。只读源、create-only写新证据、0600/0700、禁止私有数据输出。遇到HOLD报告固定SAFE原因码并停止，不得自作主张放宽SHA、替换冻结来源、重试GPU。所有公开代码提交GitHub并验证CI，不与其他Agent冲突。
