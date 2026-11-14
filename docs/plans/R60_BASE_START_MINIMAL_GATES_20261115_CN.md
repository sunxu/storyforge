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
