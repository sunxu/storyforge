# StoryForge R60 下一轮：Base 重新训练与最小有效隔离合同

日期：2026-11-15。适用工作分支：`r60/common2-cpu2-owner`。**这是工程规划和候选预演，不是训练授权或数据准入。**

## 明确选择：从冻结 Qwen Base 开始

- 基座：`Qwen/Qwen3.8-27B`，沿用冻结版本 `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`（执行前应验证远端确切revision可用及模型文件哈希）；**不加载 R46/R54 或任何旧 LoRA/optimizer 的训练状态**。
- R46 v0.2 与 R54 v0.3 仅作历史对照；若将来做同数据的R46续训，应另立实验、另授权，不冒充本次主实验。
- 当前 `339` 质量双PASS，`3` 条与五个R50已知来源之一交叉，已独立私有隔离，`336` 条只能用于只读候选预演，**不是训练/验证准入样本**。确认本地`R50_KNOWN5_QUARANTINE_SAVED__FULL_R50_HOLD`，原339报告及V1/V2/V3回执不可修改。
- 先验证数据能否提升互动文学风格、NPC主动推进、角色一致性，不能通过放宽玩家自主权和硬事实/禁令换取分数。

## 取消的历史阻塞与必须保留的最低门禁

**不再作为本次Base新实验的训练准入门禁：**R46/R54旧LoRA具体训练集逐条回放、旧optimizer继承、历史在线Provider HTTP字节级请求回放、目标当时完整System请求精确还原。历史真实System不存在时不得假称恢复；可以使用独立显式注明`TRAINING_CONSTRUCTED_NOT_HISTORICAL`的统一输入合同。仍需让上下文真实、连贯、无未来答案偷看；不得用不明来源的卡片填补事实。

**仍必须保留：**
1. 来源与授权：合法来源、冻结目标和输入哈希、质量双PASS以及无严重标记；独立审稿人的真实性/互不串评未证明时继续保持HOLD。
2. 测试隔离：R50保护故事和任何将用于独立评测的完整heldout来源、旧开发/测试来源风险必须被核实；已知3条永久排除于本批。五个已知UUID不等于全部保护世界证明；`r50_complete_exclusion_verified=false`的候选不得进入**正式**Train/Val。
3. 世界划分：Train与Val按`story_id`分组且不能交叉，必要时按实际共享人物/世界组件合并分组。一个故事出现4条候选属于允许的源采样，不是污染。
4. SFT格式：固定训练可用的真实历史和最终Assistant目标；构造System时标注非历史；freeze预期训练格式、tokenizer实际token长度、ms-swift actual collator、last-assistant-only label mask、Train/Val单独的世界哈希。
5. 模型与评测：Base+全新LoRA独立RUN_KEY；R46/R54权重只读对照。使用开发集先排查严重禁句/代写玩家行动，不得用R50密封题迭代训练；正式晋升另须独立未暴露测试。独立性和世界组件尚未知不得自动PASS。
6. 授权：所有产物保留私有；无DB更改、无GPU、无付费推理、Gold/Train准入0，直到另行确认数据门禁与训练运行。

## 已有证据与当前下一步

已通过Owner Mac SAFE：
- V3 166/166：142 PASS、18 HOLD、2 REJECT、4 TECHNICAL_HOLD；
- V123 crosswalk 339个质量双PASS，来源签名验证完成；
- 339唯一case_key/目标消息ID，173故事/会话，精确回复哈希重复0；
- 已知R50来源重合3条/1故事，私有隔离清单保存，336仍为`FULL_R50_HOLD`。

为减少等待，仅新增`experiments/r58_quality/r60_base_start_world_split_preview.py`，**只读**复核冻结V1/V2/V3、339 Crosswalk和3/336隔离清单，按故事做确定性的 80/20 预览；只输出聚合数量，无私有故事ID、不会写训练文件，336均保持HOLD。这只是工程方案形状检查，**既不是最终Train/Val切分，也不能证明跨UUID世界语义隔离**。

Mac：

```bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner

PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
"$PY" experiments/r58_quality/r60_base_start_world_split_preview.py \
  --old-dir "$BASE/r60-quality-fast1000-api-v1" \
  --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114" \
  --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1" \
  --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1" \
  --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1" \
  --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1"
```

预计`known5_excluded_cases=3`、`held_candidate_cases=336`、`train_admitted=0`，train/val仅为`provisional_`字段。下一步补齐完整R50保护来源与其他已选独立测试来源，只针对**会用于本次实验或模型晋升**的保护集执行差集；验证后才冻结正式世界切分、SFT训练格式、CPU actual tokenizer/collator。保持新Base路线，不自动提交HF任务。

## 工程与数据选择策略

主实验建议A：从Base重新训练，使用新审核/准入数据；旧R46/R54不用于初始化。未来如需回答“旧模型续训是否更省数据或提高质量”，B实验用同一冻结数据在R46 Adapter上续训，须声明追加暴露与训练步骤的差异，不能将A/B差异都归因于起点。新实验的评价结果先标开发回归，不将旧R47/R48/R55已暴露题作为正式晋升测试。R50存在已知来源重叠，绝不用于当前调参。

**执行状态：**`BASE_START_PREVIEW_ONLY__SOURCE_ISOLATION_AND_ADMISSION_HOLD`。全部安全标志维持FALSE；本文件没有批准本次训练、推理、GPU或促成任何Gold发布。


## 2026-11-15 Owner Mac首轮划分预演已确认

Owner SAFE：`BASE_START_SPLIT_PREVIEW_ONLY__ALL_HELD_NO_ADMISSION`，已知R50三条隔离；剩余336条来自172故事，确定性预览Train 276条/136故事、Val 60条/36故事，Train与Val的**story_id严格不相交**。但R50完整范围、跨UUID组件隔离、Reviewer独立性、实际Tokenizer/Collator未认证；336条仍全部HOLD，未写训练文件。

下一步不付费的静态SFT输入检查：新增`experiments/r58_quality/r60_base_start_sft_shape_cpu.py`，只读重新绑定V1/V2/V3、Crosswalk、已保存quarantine，检查336条的三消息角色`user,assistant,user`、输入和最终目标非空、历史/目标哈希不漂移，并统计目标/历史字符长度。它**不生成训练数据，不加载模型、不调用tokenizer/collator，也不自行补System或故事卡**，不会将静态格式通过冒充实际Qwen Collator通过。

Mac命令：

```bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
"$PY" experiments/r58_quality/r60_base_start_sft_shape_cpu.py \
  --old-dir "$BASE/r60-quality-fast1000-api-v1" \
  --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114" \
  --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1" \
  --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1" \
  --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1" \
  --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1"
```

预期`candidate_count=336`，`validated_three_message_cases=336`，失败分类为空（若检测出异常则HOLD），`actual_collator_last_assistant_mask_verified=false`、`real_tokenizer_verified=false`、`training_dataset_created=false`、`train_admitted=0`。继续隔离R50和其他实际用于正式测试的数据来源，待通过后再准备真实CPU tokenizer/collator与来源准入流程。


## 2026-11-15：336条真实来源静态SFT格式PASS，下一步本地CPU Tokenizer/Collator

Owner真实SAFE：`BASE_SFT_STATIC_SHAPE_PASS__ALL_HELD`，336/336冻结三消息`user,assistant,user`，历史与目标来源SHA无错误；历史字符数min227/mean680.31/max2167，目标min300/mean544.12/max1497。全部336的历史System标记`UNKNOWN_NOT_ACTUAL_SENT`，**禁止把这误认为真实历史System已复原**。Tokenizer和Collator仍未执行，train_admitted=0。

新实现：`experiments/r58_quality/r60_base_start_cpu336_template_audit.py`。复用已在`r60_common2_sft_cpu_template_audit.py`实现的Qwen3.8本地tokenizer、ms-swift`last_round`真实collator和R18严格Label Mask检查。它从冻结V1/V2/V3和独立quarantine在内存中构造4条消息(`user,assistant,user,assistant`)，不新造System/卡片；仅测试这套明确声明的**最小训练输入候选合同**，不认为它等价于有卡的产品输入。只读本地冻结`1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` tokenizer/config snapshot，不下载模型权重、不调用网络或推理、不产生训练JSONL。不在SAFE中输出各条Token数、内容、来源ID。336条继续FULL_R50_HOLD；正式训练前仍需确认如何提供合理世界规则与历史上下文。

Owner Mac同一venv执行（先token，再both）：

```bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner

PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
SNAPSHOT="/workspace/models--Qwen--Qwen3.8-27B/snapshots/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
# SNAPSHOT是示例占位路径！替换为该Mac或HF CPU环境中已存在的固定revision本地文件夹；
# 必须含tokenizer.json/tokenizer_config.json/config.json。不可自动下载GPU权重。
COMMON=(
  --old-dir "$BASE/r60-quality-fast1000-api-v1"
  --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114"
  --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1"
  --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1"
  --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1"
  --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1"
  --snapshot "$SNAPSHOT"
)
"$PY" experiments/r58_quality/r60_base_start_cpu336_template_audit.py "${COMMON[@]}" --stage token
"$PY" experiments/r58_quality/r60_base_start_cpu336_template_audit.py "${COMMON[@]}" --stage both
```

若当前环境缺少已固定snapshot，请先定位本地已存在的同revision快照，再运行，**不要将示例路径当作实际文件**。两阶段可分别返回`BASE_CPU336_TOKENIZER_PASS__COLLATOR_HOLD`与`BASE_CPU336_TOKENIZER_COLLATOR_PASS__ALL_HELD`（只有实际完成才可使用）；同时需检查`cases_checked=336`、`model_weights_loaded=false`、`training_dataset_created=false`、`train_admitted=0`。任何阶段遇错误仅SAFE阶段码HOLD，不打印敏感异常。请回传输出SAFE。

注：这只是`THREE_PERSISTED_MESSAGES_NO_SYSTEM`合同的技术诊断；正式训练输入结构、R50及世界组件排除、独立审稿证据仍需另审，不能把技术PASS等同质量PASS或GPU授权。


## 2026-11-15：转HF CPU336的可复用Quality Pipeline技术门禁（本轮尚未提交Job）

Owner Mac静态结果：`BASE_SFT_STATIC_SHAPE_PASS__ALL_HELD`、336/336来源绑定、System全部`UNKNOWN_NOT_ACTUAL_SENT`。Mac没有固定Qwen tokenizer snapshot，故改用已证实的HF CPU执行路径；**不在Mac下载完整27B权重**，HF只拉取Tokenizer、Config与模板相关文件。

严格遵循`skills/storyforge-real-quality-review/SKILL.md`与`skills/storyforge-hf-jobs/SKILL.md`：

- Quality pipeline冻结来源/双审/R50保护的业务决策在本地执行，公共`src/storyforge_dataset/hf_runtime/`提供`InputManager`/`OutputManager`/`ResourceGuard`。本次**没有增加另一套评分/质量准入逻辑**，`336 FULL_R50_HOLD`照旧。
- 技术输入`experiments/r58_quality/r60_base_cpu336_hf_packet.py`只读重新验证V123和私有隔离清单，新建独立`0600`私有**技术测试包**336行`user,assistant,user,assistant`；不构造System，不生成或归档Train/Val JSONL，不将预演276/60转成训练集。
- `scripts/r60_base_cpu336_hf_stage.py`重用`r60_common2_wrapped_hf_stage.local_dependencies(entries,extras)`与共享`InputManager`，生成不可覆盖SHA绑定Stage；完整内容和代码先于上传得到固定哈希。旧Common2 Stage不动。
- `scripts/r60_base_cpu336_hf_cli.py`将独立Bucket前缀及Worker挂载配置交给现有`r60_common2_wrapped_hf_cli`通用安全流程，继承`hf_job_guard`、RO输入/RW独立输出、单次提交marker、完整Job历史查询及dry-run，避免另写Orchestrator。**未执行`sync`/Job**。
- HF Worker`scripts/r60_base_cpu336_hf_worker.py`重用`r60_common2_sft_cpu_template_audit.inspect_rows`的真实Qwen3.8Tokenizer + ms-swift/R18严格最后轮Assistant监督检查；不加载模型权重、不GPU、不推理。原Common2审计核心中的`cases`汇总已改为`len(rows)`（2条业务结果不变），336条结果仅发布聚合min/median/p95/max，不输出逐条长度、内容、case IDs、来源哈希。
- `scripts/r60_base_cpu336_hf_receipt_verify.py`使用共享`InputManager`严格验收SAFE回执、336计数、三个长度聚合、固定Model Revision、逐门禁FALSE、run_key以及可选精确字节SHA。Job COMPLETED不等于业务技术PASS。
- 仍未完成：HF CPU真机执行、真正独立Reviewer证明、R50完整排除/跨故事组件隔离、最终有卡/统一System训练输入合同、实际Train/Validation冻结、GPU授权/训练；上述全部保持HOLD。

### Owner Mac：先执行本地纯离线预检及私有技术Stage

```bash
set -euo pipefail
set +x
umask 077
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
PACKET="$BASE/r60-base-cpu336-hf-packet-v1"
COMMON=(
 --old-dir "$BASE/r60-quality-fast1000-api-v1"
 --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114"
 --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1"
 --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1"
 --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1"
 --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1"
 --output-dir "$PACKET"
)
"$PY" experiments/r58_quality/r60_base_cpu336_hf_packet.py "${COMMON[@]}"
# 上述只读PASS后，以下只创建新的0700/0600私有技术输入：
"$PY" experiments/r58_quality/r60_base_cpu336_hf_packet.py "${COMMON[@]}" --write
RUN_KEY="r60-base-cpu336-$(date -u +%Y%m%dT%H%M%SZ)-$("$PY" -c 'import secrets; print(secrets.token_hex(6))')"
STAGE_PARENT="$BASE/r60-base-cpu336-hf-stages"
mkdir -p "$STAGE_PARENT"
chmod 700 "$STAGE_PARENT"
STAGE="$STAGE_PARENT/$RUN_KEY"
"$PY" scripts/r60_base_cpu336_hf_stage.py prepare \
 --private-dir "$PACKET" --stage "$STAGE" --run-key "$RUN_KEY"
"$PY" scripts/r60_base_cpu336_hf_stage.py verify \
 --stage "$STAGE" --run-key "$RUN_KEY"
"$PY" scripts/r60_base_cpu336_hf_cli.py cli-flags \
 --stage "$STAGE" --run-key "$RUN_KEY"
"$PY" scripts/r60_base_cpu336_hf_cli.py preflight \
 --stage "$STAGE" --run-key "$RUN_KEY"
# 记录RUN_KEY与STAGE到Owner私有位置，不上传到GitHub。
```

**上述命令不访问HF、不会提交Job**；packet第二次运行有意create-only，不要重复执行同一目录。若某一步HOLD，停止，不要改写旧Stage或删除marker。只需回传SAFE聚合。

### 后续HF执行边界（先验收Stage后再进入）

```bash
# 注意：sync会将336条私有小说对话数据发送至Owner的HF私有Bucket；
# 仅在确认来源授权、数据托管范围和安全控制后运行。
"$PY" scripts/r60_base_cpu336_hf_cli.py sync \
 --stage "$STAGE" --run-key "$RUN_KEY"
"$PY" scripts/r60_base_cpu336_hf_cli.py ready \
 --stage "$STAGE" --run-key "$RUN_KEY"
# 严禁把ready=PASS当作真实CPU验收。
# 真正的Job提交必须另行明确指令，显式使用submit --execute且只执行一次。
```

HF返回SAFE后，Owner通过`hf buckets cp`从隔离结果前缀`preflight/r60/base-start/cpu336/results/$RUN_KEY/`下载`R60_BASE_CPU336_HF_SAFE_RECEIPT.json`到私有本地0600文件，随后运行：

```bash
"$PY" scripts/r60_base_cpu336_hf_receipt_verify.py \
 --run-key "$RUN_KEY" --receipt "/实际本地0600路径/R60_BASE_CPU336_HF_SAFE_RECEIPT.json"
```

验收必须`BASE_CPU336_RECEIPT_ACCEPTED__TRAIN_HOLD`、`verified_cases=336`、`actual_collator_verified=true`、`train_admitted=0`。任何失败应保留原回执，安全诊断后新命名空间/新Run Key，不覆盖/盲重试。

**当前状态：**`BASE_CPU336_LOCAL_PIPELINE_IMPLEMENTED__HF_JOB_NOT_SUBMITTED__TRAIN_HOLD`。只允许继续CPU技术验证，不推断训练授权。


## 2026-11-15：HF CPU336真实技术审计完成（远端只读回执验证）

Owner回传SAFE，并由HF私有Bucket原路径只读获取原始918字节JSON，确认与Owner回传字段吻合。运行键`r60-base-cpu336-20261114T165256Z-9e35795990aa`，CPU Job `6af894de29dd05ff036789ed`，固定基座`Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`。回执状态`BASE_CPU336_ACTUAL_COLLATOR_PASS__ALL_HELD`、336/336、`input_sha_verified=true`、`tokenizer_verified=true`、`actual_collator_verified=true`、`last_assistant_label_mask_verified=true`。Tokenizer长度min441/median779/p95 1622/max2404；实际Collator min391/median729/p95 1572/max2354；最后Assistant监督token min192/median315/p95 736/max995。未加载权重、没有推理或GPU、没有训练数据集输出，`train_admitted=0`。

远端只读来源：`hf://buckets/adradar/storyforge-training/preflight/r60/base-start/cpu336/results/r60-base-cpu336-20261114T165256Z-9e35795990aa/R60_BASE_CPU336_HF_SAFE_RECEIPT.json`。这是**远端只读文本核实**，尚未在Owner Mac运行`r60_base_cpu336_hf_receipt_verify.py`对下载字节及完整字段执行独立接受流程，故不可伪称`BASE_CPU336_RECEIPT_ACCEPTED__TRAIN_HOLD`已由Owner本地实际产生。技术回执本身足以支持336条技术审计PASS，但不支持训练准入。

后续不可再发起同RUN_KEY HF Job。Owner可执行原有`hf buckets cp`取回SAFE JSON到0600本地私有路径，运行`scripts/r60_base_cpu336_hf_receipt_verify.py --run-key ... --receipt ...`，以获得`BASE_CPU336_RECEIPT_ACCEPTED__TRAIN_HOLD`独立验收；不得改动原远端回执。

**剩余准入门禁：**`r50_complete_exclusion_verified=false`、`reviewer_independence_verified=false`、`world_component_isolation_verified=false`，而且当前技术输入是`THREE_PERSISTED_MESSAGES_NO_SYSTEM`，不是已确认的产品System/世界卡训练合同。继续先做冻结保护来源差集、独立双审证据与语义世界组件隔离，再设计产品兼容输入；本轮GPU训练未授权，Train 0。


## 2026-11-15：336条真实Collator独立验收PASS，转向R50原始50来源精确交集

Owner Mac实测`BASE_CPU336_RECEIPT_ACCEPTED__TRAIN_HOLD`、`verified_cases=336`、`actual_collator_verified=true`，Tokenizer/Collator技术问题正式关闭，不重交HF Job；冻结输入仍为无System四消息**技术测试合同**而非产品最终训练合同。

新增只读CPU脚本`experiments/r58_quality/r60_base339_r50_original50_exact_cpu.py`，**复用**`scripts/r60_r50_original50_complement_cpu.jsonl`（R50原始50 provenance固定长度+SHA）、`scripts/r60_r50_common2_exact_source_isolation_cpu.r50_sources/source_id`、既有`identity.verified_cases_report`和`quarantine.construct`。验证冻结339候选与原始R50 50条全体的story/session/message精确ID交集；对已隔离的3条和剩余336条分别计数，SAFE只输出聚合。R50原始50 provenance已核对 ≠ R50最终密封评测封签 ≠ 跨UUID共享世界或别名语义隔离；哪怕剩余336条精确ID无交集，`r50_complete_exclusion_verified`仍强制FALSE，`train_admitted=0`。合成CI [#43620807618](https://github.com/sunxu/storyforge/actions/runs/43620807618) Ruff PASS、150 tests PASS，无GPU/请求/数据库。

Owner Mac只读验证：

```bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
# 找到原始的R50_CASE_PROVENANCE_50.jsonl，而不是派生46条的同名或替代文件。
find "$HOME/.local/share/storyforge" -type f -name 'R50_CASE_PROVENANCE_50.jsonl' -print
R50_ORIGINAL="/请填写上述实际存在的原始50条provenance绝对路径"
"$PY" experiments/r58_quality/r60_base339_r50_original50_exact_cpu.py \
 --old-dir "$BASE/r60-quality-fast1000-api-v1" \
 --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114" \
 --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1" \
 --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1" \
 --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1" \
 --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1" \
 --r50-original-provenance "$R50_ORIGINAL"
```

只有`R50_ORIGINAL50_EXACT_HELD_KEYS_DISJOINT__OTHER_GATES_HOLD`且`remaining_336_exact_key_overlap=0`才算**精确来源键**检查通过，所有准入仍HOLD。若同名文件多个，不能盲选；工具会用冻结SHA/长度校验，绝不复制或调整R50原始文件。后续才核验Reviewer独立性及跨故事语义组件，不能把现有5故事UUID核对视为完整保护的证明。


## 2026-11-15：R50原始50精确键隔离已通过，继续Reviewer证据绑定

Owner Mac实际SAFE `R50_ORIGINAL50_EXACT_HELD_KEYS_DISJOINT__OTHER_GATES_HOLD`：冻结原始50 provenance SHA校验通过、R60 339候选已核对；全部339与R50交集Story 3条/Session 3条/Message 0条，重叠3条恰好位于known5 quarantine，**剩余336条story/session/message精确键交集均为0**。该结果可以关闭“R50原始50精确ID隔离”子门禁，但不等于R50最终封签、跨UUID别名世界独立或训练准入。

新增`experiments/r58_quality/r60_base336_reviewer_provenance_cpu.py`：只读重建冻结1000 V1/V2/V3收据和339双PASS报告，精确绑定3/336 quarantine；读取V1冻结Reviewer配置，通过现有`batch.validate_config`校验，检查336条双侧`a/b`来源链、独立模型ID配置、PASS收据引用和来源版本计数。V2/V3模型ID/receipt签名绑定已由`identity.verified_cases_report`重放验证。**配置写有独立性声明也不能证明Provider实际独立执行**，回执总是`reviewer_independence_verified=false`、`train_admitted=0`。不重复请求模型、不打印模型名、URL或私有收据摘要。

Owner Mac只读命令：

```bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
"$PY" experiments/r58_quality/r60_base336_reviewer_provenance_cpu.py \
  --old-dir "$BASE/r60-quality-fast1000-api-v1" \
  --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114" \
  --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1" \
  --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1" \
  --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1" \
  --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1"
```

预期`BASE336_REVIEW_EVIDENCE_BOUND__INDEPENDENCE_HOLD`、`cases_checked=336`、a/b每侧336个有效证据。后续针对Reviewer来源独立性需单独核实Provider分路、上下文不共享的执行证据；针对World必须另做源绑定的语义组件关联（同名歧义不能直接认定），不能用story_id不相交替代。依旧Train 0、无GPU/HF Job。


## 2026-11-15：Owner Reviewer来源证据PASS（实际独立性仍HOLD），世界跨ID精确关联下一步

Owner Mac `BASE336_REVIEW_EVIDENCE_BOUND__INDEPENDENCE_HOLD`，336条全部有两个有效来源收据，冻结不同Model ID已验证：A侧V1=305/V2=27/V3=4，B侧V1=187/V2=11/V3=138。冻结V1配置`owner_attested_independent_ai=false`；`provider_execution_independence_verified=false`与`reviewer_independence_verified=false`继续HOLD。这说明证据链完整，不能推导Provider真实执行独立或无共享上下文；不要重新评分或自动补造Owner独立声明。

新增不付费`experiments/r58_quality/r60_base336_world_linkage_screen_cpu.py`，复用V123完整来源重建、private known5隔离、`split.preview`已经冻结的336/172与预演分组。以四种**精确关联**构建跨Story ID无向图：相同目标SHA、相同三消息历史SHA、相同来源Session ID、复用历史/目标Message ID。只输出不同故事关联边数、关联组件数、跨当前Train/Val预演边界组件数；无ID、世界正文、每案长度或SHA出现在SAFE。这个检查能指出可能的结构跨世界组件，但无法识别仅有同名/别名/设定相似的语义关联，`world_component_isolation_verified=false`始终保留。CI [#43622428862](https://github.com/sunxu/storyforge/actions/runs/43622428862) Ruff和159项合成测试PASS。

Mac只读运行：

```bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
"$PY" experiments/r58_quality/r60_base336_world_linkage_screen_cpu.py \
 --old-dir "$BASE/r60-quality-fast1000-api-v1" \
 --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114" \
 --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1" \
 --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1" \
 --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1" \
 --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1"
```

预期`BASE336_EXACT_WORLD_LINK_SCREEN_PASS__SEMANTIC_HOLD`。如果`cross_train_validation_components>0`，即使当前story_id分组不交叉，也已有确切结构链接跨训练验证，需要调整预演分组；如果为0，只能关闭“当前四类已知精确链接未跨组”子门禁，**不能宣称世界语义独立**。下阶段应基于源绑定的世界/角色明确关联证据，限制语义疑点候选供Owner复核，避免仅按相同中文人名误合并世界。持续`train_admitted=0`、不新建HF Job/GPU。


## 2026-11-15：Owner跨故事精确结构关联筛查真实PASS

Owner Mac SAFE `BASE336_EXACT_WORLD_LINK_SCREEN_PASS__SEMANTIC_HOLD`，`cases_checked=336`，`distinct_story_ids=172`，`exact_linked_story_pairs=0`，四类关联边`history_exact_sha/source_message/source_session/target_exact_sha`均为0，`multi_story_components=0`，`structural_components=172`，`cross_train_validation_components=0`，`structural_linked_split_disjoint=true`。此前只读276/60按story_id预演在四类**已测试的精确链接**下无需调整；但不存在跨ID链接并不证明不同UUID没有角色别名、共享世界设定或同故事不同封装，`semantic_alias_completeness_verified=false`、`world_component_isolation_verified=false`仍保持。

这一子门禁关闭后，优先确定结构化世界来源（例如原始story metadata/角色卡及可验证主键）是否存在，设计**源绑定、可追溯的语义疑点审阅**。禁止仅按通用角色名、绵绵等描述词或文本近似自动连接世界；不能把三个消息所见当作完整世界设定。不应再为已PASS的Tokenizer、R50 exact-ID、四类结构边增加重复HF Job。Reviewer执行独立性缺乏Owner原始声明和独立请求路由证据，仍HOLD；产品System输入合同也未冻结。训练准入0，GPU未启动。


## 2026-11-15：世界/角色元数据来源契约调查与336覆盖诊断

经检视当前Git代码：`r60_real_private_batch.parse_rows`从DB结果仅构造`source.story_id/session_id/assistant_message_id/prior_user_message_id/previous_assistant_message_id/previous_user_message_id/assistant_turn_index`；冻结case还保留3条history+target及`historical_system_provenance=UNKNOWN_NOT_ACTUAL_SENT`、`normalized_system_provenance=RECONSTRUCTED_NOT_ACTUAL_SENT`、`world_component_status=UNKNOWN_HOLD`。原始SQL与`r60_real_expand_private.parse_page_rows`并未提取story title、story card、character card、世界设定关系。不能根据三条聊天文本推导已知完整世界或自动合并同名角色。R57 `r57_g2_alias_name_hints`和`r57_g2_alias_pair_review`可复用“先锚定证据、标题只是hint、未审不得自动链接”原则，但其冻结八源和29/55对范围**不是R60 336样本直接来源**，不得混作同一权威素材。

新增`experiments/r58_quality/r60_base336_world_metadata_coverage_cpu.py`：只读重建V123与quarantine、复用冻结数据核验，统计实际336 case的来源字段布局、9类可选结构化世界资料字段覆盖、原始/归一化System和world_component状态的聚合覆盖。SAFE不出原文、world ID、文件位置、未知私有字段名；即使出现story_title等字段也只算覆盖，`original_story_metadata_authenticated=false`、`original_character_cards_authenticated=false`、`semantic_world_alias_complete=false`、`world_component_isolation_verified=false`。代码和4项synthetic测试经Ruff与[CI #43623302538](https://github.com/sunxu/storyforge/actions/runs/43623302538) 163/163 PASS；没有DB查询、HF Job或GPU。

Owner Mac只读命令：

```bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
"$PY" experiments/r58_quality/r60_base336_world_metadata_coverage_cpu.py \
 --old-dir "$BASE/r60-quality-fast1000-api-v1" \
 --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114" \
 --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1" \
 --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1" \
 --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1" \
 --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1"
```

预期`BASE336_SOURCE_METADATA_COVERAGE_PASS__SEMANTIC_SOURCE_HOLD`（真实覆盖计数须以Owner运行SAFE为准）。下一阶段若覆盖缺失，先调查实际Story/card等数据库实体、外键、权限与历史时点，再在Owner明确授权范围内设计**独立只读元数据source locator**及可追溯证据，不能直接发起全库敏感正文读取、生成自动假设别名或修改冻结案例。Reviewer独立性、R50最终密封/语义保护、产品System训练合同继续HOLD；Train 0。


## 2026-11-15：Owner世界元数据0/336覆盖；Supabase真实表关系与限定DB调查

Owner Mac实际`BASE336_SOURCE_METADATA_COVERAGE_PASS__SEMANTIC_SOURCE_HOLD`：`source_cases=336`，172个Story ID，来源布局仅1种，9类可选世界/角色字段覆盖率全部0，原历史System来源全部`UNKNOWN_NOT_ACTUAL_SENT`、规范System为`RECONSTRUCTED_NOT_ACTUAL_SENT`、World组件均`UNKNOWN_HOLD`。不能拿无卡片的冻结技术样本说语义世界独立；训练准入仍0。

通过**已连接StoryForge Supabase只读Schema**核实：
- `public.user_stories.id`（text）可对应冻结`source.story_id`（text）；表中有`world_setting`、`initial_system_prompt`、`characters`、`v2_data`、`updated_at`、`public_content_revision`等字段。
- `public.story_content_versions.story_id`（text，已声明外键到`public.user_stories.id`），含`content_revision`、`title`、`v2_data`、`source_updated_at`、`archived_at`等。**这些字段可以定位当前/归档来源，不能在没有按目标轮次时间与历史调用路径证据时推断当时实际发送了哪版System/世界卡**。
- `public.story_v2_sessions`有`story_id/session_id`（text）、`character_stages`、`created_at`等；`public.character_states`含`story_id/session_id/character_id`，但这些是运行态数据，不等于故事创作卡权威定义。
- `public.characters`独立角色表存在，但Schema未发现以`user_stories`为父表的直接角色卡FK。不能无依据把角色名字或单独表的ID与故事卡做自动语义JOIN。个人数据、正文、System、卡片内容均未查询/输出。

新增`experiments/r58_quality/r60_base336_story_db_locator_cpu.py`：从冻结V123收据严格重建339 candidate及3/336隔离，**仅**提取336对应172 Story ID并参数化限定`user_stories`与`story_content_versions`两张表；只返回当前故事记录覆盖、非NULL世界/System/角色JSON字段数、历史版本记录聚合数量；没有`SELECT title/world_setting/characters/initial_system_prompt/v2_data`内容，也不查全部数据。默认不读数据库（`--execute`才查），DB严格沿用`r60_real_private_batch.assert_guard`要求`r58_export_reader`、事务REPEATABLE READ READ ONLY、RLS ON、非superuser且不可bypassrls；任一失败HOLD，回滚，不写数据库。注意Schema检查不能证明Owner Mac的DB连接权限或私有内容已授权，不能推断最终输入System。

Mac首先运行只读*本地*预检：

```bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
ARGS=(
  --old-dir "$BASE/r60-quality-fast1000-api-v1"
  --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114"
  --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1"
  --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1"
  --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1"
  --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1"
)
"$PY" experiments/r58_quality/r60_base336_story_db_locator_cpu.py "${ARGS[@]}"
```

预期`BASE336_SCOPED_STORY_DB_PRECHECK__NO_DB`。**只有当Owner确认本次只读范围与数据库使用权限后**，才可在Mac已有只读DSN`R60_READONLY_DATABASE_URL`可用时加`--execute`，运行后回传仅计数SAFE。此次不取正文、角色人名、实际System内容或任何用户数据，绝不生成SFT或修改冻结文件；即使数据库匹配172条仍HOLD语义别名、历史Source version以及Reviewer真实独立性。


## 2026-11-15：172 Story DB locator首次--execute泛化HOLD与安全分类诊断修复

Owner Mac第一次`--execute`只收到`BASE336_SCOPED_STORY_DB_LOCATOR_HOLD`/`SOURCE_SCOPE_DB_ROLE_OR_RUNTIME_HOLD`，这**不能推断Story ID不存在**。原脚本异常入口丢弃具体失败阶段，已在`experiments/r58_quality/r60_base336_story_db_locator_cpu.py`修复：对`FROZEN_SOURCE`/`DB_DSN`/`DB_CONNECT`/`DB_TRANSACTION_GUARD`/`DB_STORY_AGGREGATE`/`DB_VERSION_AGGREGATE`/`DB_RESULT_VALIDATE`打固定阶段标记，异常只输出受控`reason_code`与`failure_phase`，不输出异常原文/DSN/Story ID/SQL参数/卡片内容。无误判`database_accessed=false`：失败时标记null（未确认），成功后才TRUE。原`r58_export_reader`/RLS/REPEATABLE READ READ ONLY及172 ID参数化聚合范围不变。合成回归涵盖秘密异常无泄漏，Ruff/pytest 169 PASS，[CI #43625075659](https://github.com/sunxu/storyforge/actions/runs/43625075659)。

Mac Owner拉取该分支后，用先前完全相同`--execute`命令复跑一次，观察新的`failure_phase`/`reason_code`，并只回传SAFE。若`DB_DSN`/`DSN_NOT_SET_HOLD`，检查`R60_READONLY_DATABASE_URL`是否在同一shell导出；若`DB_CONNECT`，核查只读网络/TLS/登录但禁止贴密码；若`DB_TRANSACTION_GUARD`，检查登录用户是否恰为r58_export_reader及只读/RLS防线，不要为“通过测试”禁用guard；若`DB_STORY_AGGREGATE`或`DB_VERSION_AGGREGATE`，优先核实该reader是否有相应表的SELECT权限，而不是改用管理员。保持Train 0，GPU/HF Job 0。


## 2026-11-15：Owner Scoped 172-Story DB聚合成功及下一步JSON形状审计

Owner真实SAFE `BASE336_SCOPED_STORY_DB_METADATA_COUNTS__HISTORICAL_HOLD`：172/172 `user_stories`精确ID命中，`characters`非NULL 172、`v2_data`非NULL 172，独立`world_setting`、`initial_system_prompt`非NULL均0，删除0；`story_content_versions`覆盖67个Story ID共200个版本，200/200 `v2_data`非NULL且`source_updated_at`非NULL。以上仅代表当前/归档记录字段非NULL，不能确定JSON有效内容、角色卡具体结构，更不能验证历史实际发送的System/故事版本。冻结336 SFT继续仅三消息+目标，全部HOLD不准入。

新CPU脚本`experiments/r58_quality/r60_base336_story_json_shape_cpu.py`，使用现有`locator.scoped_stories`和同一严格只读`r58_export_reader`/RLS/READ ONLY权限门禁，默认不访问DB。仅对冻结172 Story IDs，返回当前`user_stories.characters`与`v2_data`、归档`story_content_versions.v2_data`的JSONB object/array/空object/空array的**聚合数量**；无原始JSON正文、字段名、人物名字、标题、System内容或Story ID输出。不依据字段形状自动判定世界语义同一性。此工具即使检查通过，`semantic_world_alias_verified=false`、`historical_actual_sent_system_verified=false`及`train_admitted=0`不变。

Owner Mac调用：更新`r60/common2-cpu2-owner`后，
```bash
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
ARGS=(
 --old-dir "$BASE/r60-quality-fast1000-api-v1"
 --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114"
 --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1"
 --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1"
 --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1"
 --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1"
)
"$PY" experiments/r58_quality/r60_base336_story_json_shape_cpu.py "${ARGS[@]}"
# 如果已有权限确认并仍使用原严格只读DSN：
"$PY" experiments/r58_quality/r60_base336_story_json_shape_cpu.py "${ARGS[@]}" --execute
```
预期`BASE336_STORY_JSON_SHAPE_COUNTS__SEMANTIC_HISTORICAL_HOLD`，只回传SAFE计数。后续若JSON对象有实际结构，再另行确认可审核的字段合同及来源版本锚点，而非直接批量读取172条私有故事卡原文。


## 2026-11-15：Owner真实JSON结构覆盖PASS；V2运行时角色卡字段已源码锚定

Owner实际`BASE336_STORY_JSON_SHAPE_COUNTS__SEMANTIC_HISTORICAL_HOLD`：172/172当前`user_stories.characters`为**空数组[]**（非NULL≠有内容）；172/172`user_stories.v2_data`均为非空JSON object；200/200`story_content_versions.v2_data`均为非空JSON object。确认不能用顶层`characters`生成训练角色卡；v2_data对象本身非空，但其实际业务字段、语义设定和原历史请求仍未证明。

检查项目早期源码冻结`sunxu/RolePlay` commit `ccdf2e8dc2723f481cd0392883bc359e9e341c66` 的`src/app/api/chat/v2/route.ts`：V2路由直接从`storyRow.v2_data`构造`canonicalEventDraft`，经本地化得到`v2Draft`；运行时明确按`v2Draft.cardType === 'story' ? v2Draft.characters : [v2Draft.character]`选角色列表，访问`v2Draft.opening`。这是源代码合同证据，**不是**336例真实历史请求或已验证历史v2_data版本。

新增`experiments/r58_quality/r60_base336_v2_card_contract_cpu.py`：对冻结172 Story ID所匹配当前story及200条版本，仅统计`v2_data.cardType`值为story/character/缺失数量、`characters`数组类型和非空数量、`character`对象类型及`opening`、`world`**键存在性**。无原始JSON、角色名称、世界文本、UID或Prompt导出；`world`仅为可选键覆盖观察，不默认此键有业务含义。沿用R58只读用户/RLS、scope参数化、默认不访问DB。Ruff/合成`177 passed`，[CI #43626606502](https://github.com/sunxu/storyforge/actions/runs/43626606502)。所有语义/历史版本/Reviewer及训练门禁仍HOLD。

Mac Owner执行：
```bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
ARGS=(
  --old-dir "$BASE/r60-quality-fast1000-api-v1"
  --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114"
  --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1"
  --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1"
  --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1"
  --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1"
)
"$PY" experiments/r58_quality/r60_base336_v2_card_contract_cpu.py "${ARGS[@]}"
"$PY" experiments/r58_quality/r60_base336_v2_card_contract_cpu.py "${ARGS[@]}" --execute
```

预期`BASE336_V2_CARD_STRUCTURE_COVERAGE__SEMANTIC_HISTORY_HOLD`。依据聚合覆盖再决定是否需要严格源绑定的私有语义复核，禁止因为`cardType`/角色名相同自动跨UUID合并世界。


## 2026-11-15：Owner V2角色卡结构真实计数与世界值类型下一门禁

Owner Mac实际SAFE `BASE336_V2_CARD_STRUCTURE_COVERAGE__SEMANTIC_HISTORY_HOLD`：当前172条中`v2_data.cardType='story'`为157，`='character'`为0，缺失0，因此**另外15条为其他非空类型值**；历史200版本分别165/0/0，另35条为其他非空类型。当前172条`v2_data.characters`均为array，其中171条非空，1条空；200版本均为非空array；当前172条及200版本`v2_data.character`均为object；`opening`/`world`键覆盖均为172/172与200/200。注意`cardType`有其他值并不一定是不合法；已pin运行时逻辑`cardType==='story' ? characters : [character]`，因此15/35样本走非story分支，正好需要验证`character`对象结构。**字段存在/非空不等于实际发送历史System或世界语义独立。**

新增`experiments/r58_quality/r60_base336_v2_world_branch_shape_cpu.py`与合成回归；只使用172个冻结Story ID的`user_stories.v2_data`、`story_content_versions.v2_data`，聚合当前与版本的`world` JSON类型(object/array/string/null)、空对象/数组/字符串和非空对象数，`opening` JSON类型，同时统计`cardType='story'`分支的非空/空`characters`数组与**所有非story分支**的`character`对象结构。直接复用冻结V123/known5隔离、R58只读Role/RLS及已有参数化SQL安全合同；不SELECT角色名称、world文本、Prompt、JSON值或原始Story ID，也不自动判定跨UUID世界同一性。默认不查DB，显式`--execute`才查询。

Owner Mac命令：

```bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
ARGS=(
 --old-dir "$BASE/r60-quality-fast1000-api-v1"
 --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114"
 --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1"
 --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1"
 --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1"
 --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1"
)
"$PY" experiments/r58_quality/r60_base336_v2_world_branch_shape_cpu.py "${ARGS[@]}"
"$PY" experiments/r58_quality/r60_base336_v2_world_branch_shape_cpu.py "${ARGS[@]}" --execute
```

若`world`多数为nonempty object，则下一步**先审查已pin的V2 TypeScript定义中world内部允许字段/来源时间合同**，再在相同172 ID范围内做键集合计数与来源绑定审阅；不得直接导出世界内容、不按同名角色合并世界。若`world`为string/null等则按实际类型修订预期，不假造`world`结构。R50/Reviewer真实独立/历史请求/语义隔离/训练仍HOLD。


## 2026-11-15：172/200 V2 World与运行时卡片分支形状PASS；开始精确世界定义关联门禁

Owner真实SAFE `BASE336_V2_WORLD_BRANCH_COUNTS__SEMANTIC_HISTORY_HOLD`：当前172/172以及归档200/200的`v2_data.world`均为**非空JSON object**，`opening`均为JSON object；当前story分支157/157`characters`数组非空，nonstory分支15/15`character`为object；归档story分支165/165及nonstory分支35/35也符合这些对应角色路径形状。这证明冻结对应故事有当前/归档的结构性素材，不证明世界定义彼此独立、不是通用模板，也不证明历史请求使用了当前或该归档版本。

下一步转向**世界定义JSONB的精确值复用**而非继续做空/非空字段测试。新增`experiments/r58_quality/r60_base336_world_exact_value_cpu.py`：同样从冻结V123证据及known5隔离严格得到172 Story IDs，用既定`r58_export_reader` RLS/REPEATABLE READ READ ONLY角色保护；SQL在数据库内部按`v2_data->'world'` JSONB完整对象精确相等分组，仅返回四类聚合数字：非空定义值数量、跨不同Story ID共享定义组数、跨故事候选对实例数、这些组中跨预演Train/Validation的数量；分别统计当前172条、当前+200条归档版本两个范围。**数据库不会向客户端返回world JSON、摘要指纹、角色名字或Story ID；不写文件或数据库。** 当前/归档出现相同世界对象可能源于公用模板，必须视为待复核线索，**禁止自动合并世界或更改276/60预演拆分**。版本组与当时实际发送版本无绑定。代码通过Ruff与[CI #43627698135](https://github.com/sunxu/storyforge/actions/runs/43627698135)合成188测试。

Mac：
```bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
ARGS=(
 --old-dir "$BASE/r60-quality-fast1000-api-v1"
 --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114"
 --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1"
 --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1"
 --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1"
 --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1"
)
"$PY" experiments/r58_quality/r60_base336_world_exact_value_cpu.py "${ARGS[@]}"
"$PY" experiments/r58_quality/r60_base336_world_exact_value_cpu.py "${ARGS[@]}" --execute
```

预期`BASE336_WORLD_EXACT_VALUE_SCREEN__SEMANTIC_HISTORY_HOLD`。如果跨预演Train/Validation的共享定义组>0，保留隔离HOLD并人工核实是否为通用模板或真实共享世界；若=0，也只说明全对象**精确相等**未穿越，无法排除语义别名/近重复。无Reviewer独立性/R50全保护/实际历史System放行，`train_admitted=0`、GPU/HF Job 0。


## 2026-11-15：Owner发现跨预演Train/Val相同世界定义——原276/60划分进入隔离HOLD

Owner Mac真实`BASE336_WORLD_EXACT_VALUE_SCREEN__SEMANTIC_HISTORY_HOLD`：当前172个故事的`v2_data.world`有139种精确不同JSON对象，其中10组对象跨Story ID共享、共130个跨故事pair-instance，**7组跨Train/Validation预演边界**；当前+200条历史归档共152种JSON对象，10组跨故事共享、140个pair-instance，**8组跨预演边界**。此pair-instance是按每个world值组内不同Story ID组合数相加，**未验证对同一Story对的跨组去重**；不等于最终唯一故事对数。7/8为世界JSON相等的**结构候选信号**，不是7/8个已证实语义世界泄漏；标准模板或通用字段也可能精确相等。不过在消除风险前，**原276/60只能作为旧版只读划分预演，不得用于SFT准入/训练/验证隔离宣称**。禁止自动剔除候选、自动连边、自动改split或自动载入训练。

下一步先量化有多少Story ID与336条候选实际落入跨预演的精确JSON共享组，避免把7组误认为7条样本。新增`experiments/r58_quality/r60_base336_world_cross_split_impact_cpu.py`。它严格重建冻结V1/V2/V3及known5 quarantine得336条、172 Story IDs，在数据库内通过JSONB完整相等分组找出跨预演Train/Val共享`world`值；对**每种比较范围**（仅当前、当前+归档），只统计受影响的**去重Story数**与对应336条候选case数，分别按旧Train/Validation分组；不输出Story ID、世界正文/JSON、指纹、名字、版本字段，不写私有文件或数据库。仍沿用限定172 Story IDs、`r58_export_reader`、RLS ON、REPEATABLE READ READ ONLY、默认无DB/显式`--execute`。计数不能验证语义别名，也不能绑定历史actual-sent版本，全部门禁依旧HOLD。

Mac Owner只读运行：
```bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
ARGS=(
 --old-dir "$BASE/r60-quality-fast1000-api-v1"
 --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114"
 --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1"
 --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1"
 --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1"
 --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1"
)
"$PY" experiments/r58_quality/r60_base336_world_cross_split_impact_cpu.py "${ARGS[@]}"
"$PY" experiments/r58_quality/r60_base336_world_cross_split_impact_cpu.py "${ARGS[@]}" --execute
```
预期`BASE336_EXACT_WORLD_CROSS_SPLIT_IMPACT__SPLIT_HOLD`。后续先源绑定判断重复对象是泛化模板还是具体世界，以及它涉及哪些历史版本，再按证据生成私有（0600）人工/独立AI审阅问题清单；不得输出故事内容到公开Git仓库或通过公开CI读取原文。继续`train_admitted=0`、HF/GPU 0、Reviewer独立性HOLD、R50全保护HOLD。
