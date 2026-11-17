# R60 Base336：最短探索性GPU训练执行合同（2026-11-16）

> **2026-11-16 最新执行入口：** [R60 Base336 CPU336证明转移与GPU交接](R60_BASE336_CPU_PROOF_TRANSFER_NEW_AGENT_HANDOFF_20261116_CN.md)。Owner真实293/43发布包独立字节验收PASS，随后Mac真实取得`BASE336_EXPLORATORY_FINAL_COLLATOR_PROOF_TRANSFER_PASS__GPU_HOLD`：旧HF CPU336回执已接受，293+43原始行SHA多重集合与旧336完全一致，`actual_final_collator_verified=true`、`collator_executed_in_this_run=false`。**P0已完成，不要重复运行转移命令、重跑HF CPU或重建JSONL。** 下一步是按本合同实现独立R60 GPU Stage/Worker/CLI，并维护Quality Pipeline与Skills边界。GPU Job 0，`train_admitted=0`，保持探索性合同。


## Owner当前目标
仅使用冻结V1/V2/V3双PASS交集339中剔除Known5精确R50重复3条后的**336个候选**，尽快做一次Qwen Base QLoRA**探索性**训练。禁止引入Gold72、P2B、R50、旧R45或任何其他来源为本次Train/Val数据。**“只使用336候选”并不强制全部336条变成梯度样本：Train、内部Validation均必须从336池出，且不能同一条两边共用。**

本合同是新实验路线，不修改/追认既有六门禁正式准入标准。没有完整R50跨世界语义隔离、历史Provider独立证据和源时间戳来源时，不得宣称正式训练准入或模型晋升。真实训练输出状态只能是 `EXPLORATORY_GPU_..._NOT_PROMOTED`。

## 已验证可以直接复用
- `r60_real1000_candidate_identity_audit.verified_cases_report` 严格重建冻结339候选；
- `r60_real1000_r50_known5_quarantine.construct` 与已保存隔离文件恒等对照，原3条永久隔离；
- R50完整原始50条的story/session/message精确ID差集已有Owner检查PASS，不能冒充跨UUID语义隔离；
- 已验收的HF CPU336实际Qwen3.8 tokenizer / ms-swift collator / R18 last-assistant-only mask，**无需重复CPU336无System技术包**；
- 冻结336的A/B质量回执、评审模型来源和双PASS已验证（Provider独立认证HOLD）；
- `r60_base336_world_cross_split_private_roster_cpu.py`已创建8组私有roster，涉及38 Story/82条；7通用模板、1语义证据不足，当前全部HOLD；
- GPU实现复用R54 `scripts/v03_r54_gpu_runner.py`所证明的**方法与校验模块**，不能直接运行该脚本：R54 hardcode 31/9、dataset SHA、16步及老release。
- HF当前远端只有`preflight/r60/base-start/cpu336/runs/r60-base-cpu336-20261114T165256Z-9e35795990aa`技术Stage，**不是GPU训练release**。

## 唯一新批次路线：冻结336子集的训练和内部验证
1. Owner Mac只读核验原339 crosswalk + 已保存3/336 quarantine + 原始50精确隔离Owner回执 + 8组原始roster SHA；不得重做336条文学评审、不得补抽数据。
2. 按Story的确定性旧hash划分作为初始方案，读取8组roster中确证**相同JSON world**的Story连通边；把**整个跨旧Train/Val的连通组件统一归Train**，并再次重算全局组件划分。不得只挪样本，必须挪整个Story/组件；不得把`7个通用模板`自动称为语义同世界，也不得把相同JSON导致的跨组边忽略。
3. 从336中生成不相交`train.jsonl`和`validation.jsonl`，每条只有已验证3条历史user/assistant/user + 原冻结assistant target监督，明确`THREE_PERSISTED_MESSAGES_NO_SYSTEM`实验合同；不要伪造Source-bound世界卡或历史实际System。世界/卡缺失影响外推，应作为实验限制而不是隐性补写。
4. 划分验收：训练+验证总数336（除非明确产生新的隔离清单，严禁悄悄丢行）；3条Known5永不出现；无任何case跨组；story_ID不跨组；8组关联component不跨组；各split非空；保持原始目标hash、输入三消息及来源hash；评测保护只声明已证实的原始50**精确ID**差集，任何未确认的语义关系显式HOLD。
5. 在Owner Mac新建0700/0600、create-only的新私有发布目录，保存输入证据SHA、split组件信息与`train.jsonl`/`validation.jsonl`、来源336身份及格式审计回执、`EXPLORATORY_ONLY__NO_TRAIN_ADMISSION`标签。**不得复用HF CPU336技术Stage或R54正式release**。
6. **已完成**：最终293/43发布包通过独立SHA/结构验收；随后旧336真实HF CPU Collator/R18 Mask证明通过原始行字节SHA多重集合完全一致性严格转移。Owner SAFE为`BASE336_EXPLORATORY_FINAL_COLLATOR_PROOF_TRANSFER_PASS__GPU_HOLD`。不得再跑CPU336 Job或重建数据。若后续改变输入/模板/掩码合同，才按变化范围重新评估实际CPU审计。
7. GPU新建R60独立run_key和Bucket前缀`experiments/r60-base336-exploratory/<RUN_KEY>`，输出和stage强制create-only；从R54复制参数合同：`Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`、NF4/bfloat16、LoRA rank64/alpha128/dropout0.05、max_length16384、last_round、1 Epoch。**训练步数、eval/save节奏必须按实际最终Train数量计算**，并保证最后一步checkpoint与adapter reload。不能沿用R54的16step和硬编码SHA。
8. GPU发送前严格验证私有stage完整文件清单、SHA、model revision、ms-swift/transformers/bitsandbytes版本、单A100-80GB VRAM、资源额度、Bucket RW隔离和GPU计费任务的唯一提交锁。先写submit marker再提交；不自动重试不覆盖旧Run。用户本轮“尽快推进GPU训练”作为推进新实验的请求，但GPU提交仍必须以实际Stage可核验且预检PASS为前提。
9. 开始模型评测时，旧R47/R48/R55已暴露20题只能作为开发回归；R50在世界语义/曝光未完成审计前不能声称正式独立测试。Gold72/P2B既不作为训练源，也不必自动提升为本轮正式独立测试；其历史暴露用途需留档。

## 不做的工作
不重做Gold72/P2B全量Story身份扫描作为**本探索性GPU试验**的强制前提；不重跑336×2双Reviewer；不全面重审16条试验批次；不从336以外新增训练样本；不做R46/R54旧LoRA续训；不变更正式训练的A/B/HOLD历史结论。

## 当前真实状态
- `FROZEN_336_CANDIDATE_TECHNICAL_PASS__GPU_RELEASE_NOT_PREPARED`
- GPU训练数据release与可独立提交的R60 GPU worker**尚未生成**。
- 不得用已有CPU技术Stage直接作为可训练正式发布包。
- 未提交GPU Job，`train_admitted=0`，未通过独立测试集模型晋升。

## 交付清单（只输出SAFE）
本次实验有效执行前应得到：336原始身份匹配统计、Train/Val数量、两组Story数量、跨组已知World JSON组件数=0、Known5排除=3、R50原始50精确身份交集=0、各数据文件SHA、真实Collator PASS、固定GPU模型配置SHA、独立GPU RUN_KEY、远端Bucket stage READY回执。任一校验失败则不submit并说明HOLD类别，不伪称GPU已启动。


## 2026-11-16：336专用划分器已实现，Owner Mac下一条命令

代码：`experiments/r58_quality/r60_base336_exploratory_split.py` + `test_r60_base336_exploratory_split.py`；CI [#43743627660](https://github.com/sunxu/storyforge/actions/runs/43743627660) Ruff PASS、291项测试PASS。此处CI是**合成336行**，没有访问Mac真实私有文件，**尚未产生实际Train/Validation JSONL，也未提交GPU**。

本脚本沿用`identity.verified_cases_report`、`quarantine.construct`、`audit.prepare`、`preview.preview`和已保存8组World私有roster，不开发第二套原始数据提取、训练格式或模型评分器。8组中的同World JSON成员（含历史版本）作为保守的不可跨split约束；保持其他Story原始确定性slot，混合Train/Val的已知组件整体调整到Train，最终重新核验8组均不跨split。此前82条仅说明已知World风险范围；此方法不能证明语义世界隔离或R50跨世界不相交，结果必须只标`EXPLORATORY`。

**在Owner Mac执行，仅可安全显示SAFE聚合：**

```bash
set -euo pipefail
set +x
umask 077
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner

PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
RUN_KEY="r60-base336-exploratory-$(date -u +%Y%m%dT%H%M%SZ)-$("$PY" -c 'import secrets; print(secrets.token_hex(6))')"
OUT="$BASE/$RUN_KEY"
COMMON=(
  --old-dir "$BASE/r60-quality-fast1000-api-v1"
  --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114"
  --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1"
  --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1"
  --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1"
  --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1"
  --roster-dir "$BASE/r60-base336-world-cross-review-20261115"
  --output-dir "$OUT"
)
"$PY" experiments/r58_quality/r60_base336_exploratory_split.py "${COMMON[@]}"
# 仅上一行返回BASE336_EXPLORATORY_SPLIT_PREFLIGHT__NO_WRITE才执行:
"$PY" experiments/r58_quality/r60_base336_exploratory_split.py "${COMMON[@]}" --write
# output只在0600的Owner Mac私有目录；不要上传/打印正文。
```

验收：`candidate_rows=336`、`train_rows+validation_rows=336`、两侧非零、`known_world_cross_split_groups=0`、`train_admitted=0`、`gpu_started=false`，并确认`OUT`中仅有`train.jsonl`、`validation.jsonl`和SHA绑定Manifest、权限0600。**CPU旧技术Stage不允许代替这三个文件**。

下一阶段：用最终字节SHA执行现有ms-swift真实Collator/LabelMask验证、为本R60 release实现独立且不可覆盖的GPU Stage与R54的已验收QLoRA运行方案绑定；严禁直接运行写死31/9、16步及旧SHA的R54 submit脚本。没有Owner Mac发布结果前，`GPU_STAGE_READY=false`、GPU Job 0。


## 2026-11-16：真实Mac写盘HOLD定向修复

Owner真实SAFE：`BASE336_EXPLORATORY_SPLIT_PREFLIGHT__NO_WRITE`，293 Train / 146 Story、43 Val / 26 Story，共336条，`known_world_cross_split_groups=0`；随后`--write`泛化`BASE336_EXPLORATORY_SPLIT_HOLD`，**未确认实际文件创建到哪一步**。源检查发现旧`private.write_new`有200000字节单文件上限，和新数据集最大4MB合同不一致；这是一个具体、可重现的潜在根因，无法仅凭泛化HOLD确认唯一原因。

修复`r60_base336_exploratory_split.py`：数据集改用有4MB严格上限的本模块`_write_dataset_new`（O_EXCL/O_NOFOLLOW、0600、flush/fsync）；Manifest继续旧200KB保护接口；写盘前完成数据大小检验，文件和目录一律create-only。加入210KB回归测试及≥4MB拒绝测试。GitHub Actions [#43789265866](https://github.com/sunxu/storyforge/actions/runs/43789265866)：Ruff PASS，293项pytest PASS。

**只重试写盘一次，必须用全新run key**；任何上一轮留下的输出目录、部分文件都不要删除、覆盖或复用。先`git fetch/merge --ff-only`更新脚本，然后在此前命令中只重新生成`RUN_KEY`和`OUT`，调用`--write`。不要把新JSONL公开上传或打印。

成功后必须本地只读验证：`train.jsonl`确实293行、`validation.jsonl`确实43行；文件权限0600、大小<4MB，Manifest SHA与字节精确匹配；目录0700；无其他未知文件。若仍HOLD，保持输出原样，使用安全阶段码检查，不通过暴露异常/路径/正文来诊断，GPU保持零。


## 2026-11-16：真实293/43数据发布成功，新增独立字节验收器

Owner真实`--write`回执为`BASE336_EXPLORATORY_SPLIT_CREATED__GPU_HOLD`、293 Train / 146 Story、43 Validation / 26 Story、336总计，已知World跨组=0；create-only发布目录：`$HOME/.local/share/storyforge/r60/private/r60-base336-exploratory-20261116T020325Z-4314ad84d5cc`。**尚未独立二次读取这三个私有文件/校验字节SHA；不能仅凭成功写盘回执称最终发布验收PASS**。

实现`experiments/r58_quality/r60_base336_exploratory_release_verify.py`和测试：只读、0600/0700、文件集必须恰好三个、Manifest固定schema/336/293/43/世界跨组0/风险声明保留、独立重算两份JSONL SHA、逐行四消息和最后Assistant结构检查；不可篡改旧manifest，无GPU、模型、网络或DB。CI [#43790052539](https://github.com/sunxu/storyforge/actions/runs/43790052539)：Ruff PASS、298项合成测试PASS。真实Owner Mac运行命令：

```bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
OUT="$HOME/.local/share/storyforge/r60/private/r60-base336-exploratory-20261116T020325Z-4314ad84d5cc"
"$PY" experiments/r58_quality/r60_base336_exploratory_release_verify.py --release-dir "$OUT"
```

必须收到`BASE336_EXPLORATORY_RELEASE_BYTES_VERIFIED__GPU_HOLD`、`sha256_verified=true`、293/43、`train_admitted=0`，才能准备后续真实Collator审计Stage和独立R60 GPU runner。**不可用R54脚本直接提交**，旧CPU336 remote TECHNICAL Stage也不等于GPU发布包。当前`gpu_stage_prepared=false`、`gpu_started=false`。


## 2026-11-16：293/43真实发布包独立字节验收PASS，CPU336 Collator复用证据门禁

Owner实际SAFE：`BASE336_EXPLORATORY_RELEASE_BYTES_VERIFIED__GPU_HOLD`，`manifest_verified=true`、`sha256_verified=true`，293/43。只证明发布包三文件完整、逐行原始格式正确；不能称GPU已启动。

新的`experiments/r58_quality/r60_base336_exploratory_collator_transfer.py`完全只读：校验Owner Mac旧`R60_BASE_CPU336_TECHNICAL_NOT_ADMITTED_PRIVATE.jsonl`原始字节SHA与HF已执行CPU336 Stage原始source SHA相同；复用`scripts/r60_base_cpu336_hf_receipt_verify.accept`对原HF回执做严格接受；再比较旧336行和新293+43行**原始JSONL行字节SHA多重集合一致**。匹配才可把之前真实ms-swift Collator/R18 Mask验证的技术结果转移到重新划分后的同一批样本；此轮不再跑Tokenizer或Collator，不虚称二次执行。若最终配置更改System、世界卡、模板或标签算法，此复用立即失效，须重新实际执行CPU审计。原R50语义、Provider独立、正式训练准入仍HOLD。

源技术Stage事实由HF Bucket只读核验：
`preflight/r60/base-start/cpu336/runs/r60-base-cpu336-20261114T165256Z-9e35795990aa/SHA256_MANIFEST_PRIVATE.json`，源数据SHA在代码常量中固定、不在SAFE stdout显示；旧CPU336回执保留原名且须验收成功。CI [#43790711112](https://github.com/sunxu/storyforge/actions/runs/43790711112)：Ruff PASS、304测试PASS。

Mac命令（下载旧SAFE审核回执，不上传任何小说或候选数据，不覆盖现存文件）：

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

若Owner旧技术包位于不同的0600目录，替换`TECHNICAL`为原已经存在且保留的对应目录，**不可重新构造一份新技术包来冒充原HF审核输入**。成功应是`BASE336_EXPLORATORY_FINAL_COLLATOR_PROOF_TRANSFER_PASS__GPU_HOLD`、`all_final_rows_byte_identical_to_audited_rows=true`、`actual_final_collator_verified=true`、`collator_executed_in_this_run=false`、`gpu_started=false`。失败为HOLD，需复核真实来源而不是关闭哈希检查。

## Quality Pipeline 与代码复用边界（2026-11-16，实施时必须遵守）

### Quality Pipeline：只消费冻结证据，不制造新事件

- 293/43来自已冻结336候选；本实验不重做336×2文学评审，不改Gold/R50/Review历史，不创建新的Quality评分器、Rubric、Manifest或Admission入口。
- Gold Quality Pipeline只保留原有A/B审核和仲裁事件。本次Collator证明转移SAFE不得导入为Review、Source、Exclusion或Reconciliation事件；不运行 `append-review`、`import-review-reconciliation`。
- 技术PASS与质量PASS分离：`quality_v1_admitted=0`、`train_admitted=0`；Reviewer执行独立性、R50语义隔离和完整World语义隔离仍HOLD。训练若获授权，只能是探索性结果，`EXPLORATORY_*__NOT_PROMOTED`。

### 组件复用矩阵

| 层 | 复用现有实现 | R60允许新增的最小差异 |
|---|---|---|
| 数据身份/发布 | `r60_base336_exploratory_split.py`、`r60_base336_exploratory_release_verify.py`、`r60_base336_exploratory_collator_transfer.py` | 只读绑定真实P0 SAFE与Manifest；不重建JSONL |
| 输入/输出/诊断 | `storyforge_dataset.hf_runtime.InputManager`、`OutputManager`、`DiagnosticReporter` | GPU业务回执Schema和训练阶段SAFE字段 |
| Stage依赖闭包 | `r60_common2_wrapped_hf_stage.local_dependencies(entries, extras)` | R60 GPU专属入口文件、配置和固定依赖文件清单 |
| HF CPU审计 | `r60_common2_sft_cpu_template_audit.inspect_rows`、R18 Label Mask | 不新增Token算法/Collator；本次证明已转移，不重跑 |
| HF CLI/远端检查 | 复用Common2的Bucket文件集检查模式、`r60_common2_hf_cpu_final_read_only.walk_job_history`分页Job历史检查 | 独立GPU Flavor/命令参数和R60专属输入/输出前缀；不能调用CPU提交策略 |
| GPU训练方法 | `v03_r54_gpu_runner.py`中的设备资格/QLoRA/训练门禁；`hf_job_runner.py`中的`training_evidence`、`make_inference_input`、`check_inference_result`、`GpuMonitor`通用辅助 | R60数据SHA、293/43数量、训练步数、保存/评估计划、SAFE输出与独立Run Key；不复制已有通用函数 |

### 禁止的错误复用

- `scripts/hf_job_guard.py`和Common2 CPU CLI的Flavor/提交策略只允许CPU；不可通过绕过校验或修改CPU Guard来提交GPU。
- R54 Runner/Stage/Submit只作方法参考；不能复用31/9 SHA、16步、R54 release、旧Run Key或旧Bucket前缀。
- R54将整个项目Bucket RW挂载的旧拓扑不适用于新R60：输入必须精确前缀RO，输出必须独立前缀RW，二者不得重叠；不能为方便而将整桶RW。
- 不复制 `token_preflight.py`、R18 mask、Gold Quality Manifest、HF Runtime、Job历史分页和SAFE写入算法。只有证明某个通用能力缺失且至少存在明确复用场景，才考虑提取共享核心；单次实验差异先放薄适配器。
- 不把完整训练日志、任意异常、Prompt、私有路径、样本ID、正文或目标文本输出到HF Job stdout/logs；只发布SAFE状态和允许的聚合统计。

### R60 GPU链路阶段（GPU Job仍为0）

1. Mac只读检查：当前分支/HEAD/工作树、293/43 Manifest、P0 SAFE、固定模型Revision和已存在证据；不重复跑已完成的release verify/transfer。
2. 生成唯一私有Stage（0700/0600、create-only），只放293/43输入、Manifest、P0 SAFE、固定配置、必要代码和依赖闭包；每个文件SHA绑定。私有输入不得进入GitHub或CI。
3. Stage Worker只读挂载；结果使用独立唯一前缀RW挂载。远端文件清单必须与本地Manifest精确一致；组织Job历史必须完整分页，确认该Run Key无既有Job/提交marker/结果文件。
4. HF CLI参数、Flavor、镜像Digest、依赖版本、Volume RO/RW和dry-run逐项核验。dry-run只代表参数可解析，不代表GPU已提交。
5. Worker先校验Stage完整SHA、模型Revision、数据SHA/行数、依赖和单A100 80GB可用性；全部PASS后才下载固定Revision模型权重并开始QLoRA。
6. 训练步数按真实293行、per-device batch、gradient accumulation、world size和epoch计算；eval/save计划必须确保真实终端Optimizer Step有Checkpoint。训练后验证末步状态、Adapter Reload、SAFE回执和私有产物SHA。
7. 唯一Run Key提交前先写O_EXCL marker；GPU提交单次、不自动重试。未获针对该Run Key、Flavor、时长、模型Revision、配置和预算的Owner明确授权，只能到远端READY + dry-run，不能提交付费Job。

## 2026-11-17 实现状态：Stage / Worker / CLI 已落地

### 实际代码入口

| 文件 | 实现 |
|---|---|
| \`scripts/r60_base336_gpu_contract.py\` | 统一293/43、P0证明、模型Revision、训练配置和Stage SHA合同 |
| \`scripts/r60_base336_gpu_stage.py\` | Mac私有Stage创建/验签；0700目录、0600文件、O_EXCL、干净分支与工作树 |
| \`scripts/r60_base336_gpu_worker.py\` | Stage复核、A100设备/磁盘/依赖门禁、固定模型下载、QLoRA、终端Checkpoint和Adapter Reload |
| \`scripts/r60_base336_gpu_worker.sh\` | HF容器入口；先校验Stage，再装依赖，最后运行Worker；私有日志不输出到Job stdout |
| \`scripts/r60_base336_gpu_cli.py\` | 本地预检、Bucket同步、远端完整文件集/SHA复核、分页Job历史和HF dry-run |
| \`requirements/r60-base336-gpu.in\` | 固定ms-swift / Transformers / bitsandbytes / qwen-vl-utils / HF Hub版本 |
| \`tests/test_r60_base336_gpu_pipeline.py\` | Stage篡改、SHA、权限、训练步数、Checkpoint、CLI无提交等合成测试 |
| \`.github/workflows/r60-base336-gpu-pipeline.yml\` | 离线合成CI；不连接HF、不下载模型、不启动GPU |

### 复用实现

- Stage依赖闭包直接调用 \`r60_common2_wrapped_hf_stage.local_dependencies(entries, extras)\`；不再写第二套AST依赖收集器。
- Worker直接复用 \`hf_job_runner.py\` 的 \`GpuMonitor\`、\`training_evidence\`、\`make_inference_input\`、\`check_inference_result\`。
- 输入/输出校验和SAFE发布复用 \`storyforge_dataset.hf_runtime.InputManager\` / \`OutputManager\`。
- 293/43原始发布继续调用既有 \`r60_base336_exploratory_release_verify.verify\`；新增 \`verify_staged\` 只解决HF只读Stage路径不在Owner Mac private.BASE下的问题，校验算法/数据合同保持相同。
- HF CLI复用 \`r60_common2_wrapped_hf_cli.remote_set\`、\`r60_common2_hf_cpu_final_read_only.walk_job_history\` 和 \`hf_job_guard.build_hf_argv\`。**只复用通用argv构造，不调用CPU-only \`validate_spec\`，也不放宽CPU Guard。**
- R54 Worker、31/9 SHA、16步Gate和整Bucket RW Stage均不进入R60 Stage依赖闭包；没有复制R18 Label Mask、Token Preflight或Gold Quality逻辑。

### HF安全合同

- Bucket：\`adradar/storyforge-training\`。
- 输入：\`preflight/r60/base336-gpu/runs/<RUN_KEY>/\`，挂载 \`/input/r60-base336:ro\`。
- 输出：\`experiments/r60-base336-exploratory/<RUN_KEY>/\`，挂载 \`/output:rw\`；两个前缀不重叠。
- Namespace：\`adradar\`；Flavor：\`a100-large\`；Timeout：120m；镜像固定为 \`pytorch/pytorch@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee\`。
- Stage同步先上传所有文件，最后上传SHA Manifest；READY阶段逐个下载远端对象回Mac并与本地SHA比较，同时要求远端文件集完全相同。
- Job历史使用既有分页器完整走完，不以最近N条记录推断“没有Job”。
- dry-run设置 \`STORYFORGE_R60_BASE336_GPU_SCOPE=DRY_RUN_NOT_AUTHORIZED\`；Worker只接受真实Scope值 \`R60_BASE336_293_43_ONE_EPOCH_A10080GB\`。即使有人误删dry-run参数，Worker Shell也会因Scope不符而拒绝执行。
- CLI动作列表**没有submit**。当前只能执行 \`preflight\`、\`sync\`、\`ready\`、\`diagnose\`、\`cli-flags\`；不具备付费Job提交路径。

### Owner Mac下一步（仅Stage / HF READY / dry-run）

已知293/43发布目录：
\`$HOME/.local/share/storyforge/r60/private/r60-base336-exploratory-20261116T020325Z-4314ad84d5cc\`。

P0最终SAFE在聊天中已确认，但没有可确认的持久文件路径。Owner需将已确认SAFE JSON保存为0600私有文件（下面命令中的JSON即该SAFE，不是重新运行CPU或重新计算证明）：

\`\`\`bash
BASE="$HOME/.local/share/storyforge/r60/private"
RELEASE_DIR="$BASE/r60-base336-exploratory-20261116T020325Z-4314ad84d5cc"
PROOF_DIR="$(mktemp -d "$BASE/r60-base336-proof-XXXXXXXX")"
chmod 700 "$PROOF_DIR"
umask 077
cat > "$PROOF_DIR/BASE336_COLLATOR_TRANSFER_SAFE_PRIVATE.json" <<'JSON'
{
  "actual_final_collator_verified": true,
  "all_final_rows_byte_identical_to_audited_rows": true,
  "collator_executed_in_this_run": false,
  "formal_source_admission_verified": false,
  "gpu_stage_prepared": false,
  "gpu_started": false,
  "input_contract": "THREE_PERSISTED_MESSAGES_NO_SYSTEM",
  "private_values_emitted": false,
  "schema": "storyforge_r60_base336_exploratory_collator_transfer_safe_v1",
  "source_cpu_audited_rows": 336,
  "source_cpu_receipt_accepted": true,
  "status": "BASE336_EXPLORATORY_FINAL_COLLATOR_PROOF_TRANSFER_PASS__GPU_HOLD",
  "train_admitted": 0,
  "train_rows": 293,
  "validation_rows": 43
}
JSON
chmod 600 "$PROOF_DIR/BASE336_COLLATOR_TRANSFER_SAFE_PRIVATE.json"
\`\`\`

从仓库根目录执行。Stage Builder会强制当前分支为 \`r60/common2-cpu2-owner\` 且Git工作树干净：

\`\`\`bash
test "$(git branch --show-current)" = "r60/common2-cpu2-owner"
test -z "$(git status --porcelain)"
BASE="$HOME/.local/share/storyforge/r60/private"
RUN_KEY="r60-base336-gpu-$(date -u +%Y%m%dT%H%M%SZ)-$(openssl rand -hex 6)"
STAGE="$BASE/$RUN_KEY"
PYTHONPATH=src:scripts:experiments/r58_quality \\
python scripts/r60_base336_gpu_stage.py prepare \\
  --release-dir "$BASE/r60-base336-exploratory-20261116T020325Z-4314ad84d5cc" \\
  --proof-receipt "$PROOF_DIR/BASE336_COLLATOR_TRANSFER_SAFE_PRIVATE.json" \\
  --stage "$STAGE" --run-key "$RUN_KEY"
PYTHONPATH=src:scripts:experiments/r58_quality \\
python scripts/r60_base336_gpu_stage.py verify --stage "$STAGE" --run-key "$RUN_KEY"
PYTHONPATH=src:scripts:experiments/r58_quality \\
python scripts/r60_base336_gpu_cli.py preflight --stage "$STAGE" --run-key "$RUN_KEY"
\`\`\`

仅当前三步均PASS后才执行远端同步和预检：

\`\`\`bash
PYTHONPATH=src:scripts:experiments/r58_quality \\
python scripts/r60_base336_gpu_cli.py sync --stage "$STAGE" --run-key "$RUN_KEY"
PYTHONPATH=src:scripts:experiments/r58_quality \\
python scripts/r60_base336_gpu_cli.py ready --stage "$STAGE" --run-key "$RUN_KEY"
\`\`\`

\`sync\`将293/43私有数据和必要Worker代码上传到独立RO输入前缀；\`ready\`将远端对象下载回Mac逐个SHA验收、完整分页Job历史，并执行HF CLI dry-run。**这两步都不会提交Job。** 如果sync部分失败，不能用同一Run Key重传/覆盖；先diagnose，随后使用新Run Key重新Stage。

### 当前验证边界

- GitHub Base336 GPU synthetic-only workflow：Ruff、语法、Stage/Worker/CLI测试及共享Runtime/R54回归均PASS。
- REAL1000 Quality Reviewer synthetic-only workflow：对release verifier staged只读模式的回归PASS。
- CI未下载Qwen权重、未访问HF Hub、未启动CUDA、未提交HF Job。
- 尚未在Owner Mac执行真实私有Stage、HF Bucket同步、远端READY或CLI dry-run；不得把CI PASS表述成Mac/HF实测PASS。
- GPU Job仍为0；\`quality_v1_admitted=0\`、\`train_admitted=0\`；正式质量准入仍HOLD。
