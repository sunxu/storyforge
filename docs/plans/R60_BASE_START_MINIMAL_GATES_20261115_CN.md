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
