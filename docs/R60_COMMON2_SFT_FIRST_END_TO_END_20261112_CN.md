# StoryForge R60 — 2条质量PASS候选的首个SFT输入端到端验收

## 2026-11-12 Owner真实构造成功，直接推进Qwen CPU Tokenizer/Collator

Owner实际SAFE回执`storyforge_r60_common2_sft_experimental_safe_v1`：`COMMON2_SFT_EXPERIMENTAL_2_READY__TRAIN_HOLD`，`cases=2`、`input_window=11`、`system_prompt_fabricated=false`、`input_kind=SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT`、`tokenizer_verified=false`、`collator_verified=false`、`full_r50_exclusion_verified=false`、`train_admitted=0`、模型/GPU 0。**两行来源绑定私有实验SFT JSONL真实已在Owner Mac上生成**；这是数据构造阶段PASS，不代表训练准入完成。

下一步新增`experiments/r58_quality/r60_common2_sft_cpu_template_audit.py`及`tests/test_r60_common2_sft_cpu_template_audit.py`。该工具先核对现有实验JSONL/清单sha与role顺序，不含System和世界卡，**仅支持本次实际构造的11条窗口**，避免未经审查更改窗口；使用本地已固定的Qwen tokenizer快照 revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`，`local_files_only`/HF offline，明确token上限16384，禁止下载。先用`--stage token`实际测试 tokenizer；只有ms-swift和依赖在Owner本地已可用时再用`--stage both`，复用现有`scripts/hf_label_mask_audit.audit_row`验证`last_round`只监督最后Assistant、再检查实际ms-swift模板/collator标签一致性。**严格吞掉所有内部诊断/异常原文**，只回SAFE计数；不会加载完整模型、不会产生GPU训练。即使both通过，`r50_complete_exclusion_verified=false`、`train_admitted=0`。

Owner Mac CPU命令（在确认新提交CI PASS且现有工作树干净后）：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
python3 -m pytest -q tests/test_r60_common2_sft_cpu_template_audit.py
BASE="$HOME/.local/share/storyforge/r60/private"
INPUT_DIR="$BASE/r60-real1000-common2-sft-experimental11-v1"
# 只能填已在本机下载并固定revision的Qwen tokenizer路径；
# 不能把任意最新版或不明快照伪称冻结revision。
TOKENIZER_SNAPSHOT="/已有真实Qwen tokenizer本地快照/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
test -f "$INPUT_DIR/R60_COMMON2_SFT_EXPERIMENTAL_MANIFEST_PRIVATE.json"
test -f "$TOKENIZER_SNAPSHOT/tokenizer.json"
python3 experiments/r58_quality/r60_common2_sft_cpu_template_audit.py \
 --input-dir "$INPUT_DIR" --snapshot "$TOKENIZER_SNAPSHOT" --stage token
# 仅在本机已安装匹配的ms-swift及完整离线依赖后单独执行：
python3 experiments/r58_quality/r60_common2_sft_cpu_template_audit.py \
 --input-dir "$INPUT_DIR" --snapshot "$TOKENIZER_SNAPSHOT" --stage both
```

预期`COMMON2_CPU_TOKENIZER_PASS__COLLATOR_R50_HOLD`或`COMMON2_CPU_TOKENIZER_COLLATOR_PASS__R50_TRAIN_HOLD`。若本地没有已pin的tokenizer，回`COMMON2_CPU_TEMPLATE_AUDIT_HOLD`即停，不能悄悄改model revision、在线加载模型权重或启动HF Job。此前R50整体保护集没有完整对账回执，后续须单独复核冻结R50数据的来源ID和训练story/session/message重叠，绝不能仅使用五个已知故事。Wave40仍暂停。


日期：2026-11-12。**本任务优先于Wave40追加盲审。** 目标是先把既有独立六维PASS 2/2和真实持久化历史（103/243）连成一条可复现的SFT输入样例，查清真实瓶颈，然后才扩大优质数据精筛规模。不自动将PASS升级为训练准入，不申请GPU，不访问RolePlay生产。

## 事实与当前状态

- Real1000：冻结1000条完成目标，技术初筛不等于文学质量PASS。
- Common2：经不查看既有模型票的独立盲审，六维质量PASS 2/2；而非全部Real1000通过。
- 原数据库按同一story/session/assistant target只读回收了103与243条持久化完成消息，尾三消息与冻结Real1000完全对应。此前Source确证，不代表当年实际LLM请求包含这些全部消息。
- 实际发送的System、世界卡与动态记忆未验证。不能取今天的`v2_data`当成历史有效设定；不应把“还原当年Prompt”继续设为**构造实验性SFT输入**的先决条件，但必须标为衍生输入。
- R50全量隔离、训练tokenizer、ms-swift实际collator、label mask仍未验收：**正式训练准入0/2**。
- 2026-11-12已单独从Real1000成功选出Wave40，40故事、字数分布20/16/4、与Sample100重叠0；该批只是待审位置，**保留且暂停进一步盲审，不销毁、不重抽样、不占用当前关键路径**。

## 本轮新增可复用实现

`experiments/r58_quality/r60_real1000_common2_sft_experimental_cpu.py`与`tests/test_r60_real1000_common2_sft_experimental_cpu.py`：

1. 再次调用`quality.frozen_pool`验证原Real1000锁定来源；按源`assistant_message_id`、story/session、target turn，与Owner私有已恢复历史精确绑定。
2. 调用现有`common.validate`重新确认独立六维PASS 2/2，并验证每条冻结三消息与盲审输入中的目标回复、原始文案完全相同；凡原审批、来源和角色对账不一致立即HOLD。
3. 从每条恢复历史**最近11条**提取真实role/content，作为当前实验选择的窗口（默认；7/23条为有界对照选项）。这并不表示当年请求实际发送11条。要求以user开头、user/assistant严格交替、最后一条为user；若真实数据不满足则整体HOLD、人工判断裁剪策略，禁止偷偷删条或拼系统设定。
4. 仅把冻结Real1000中的原目标Assistant内容接在最后；记录`supervision_scope=FINAL_ASSISTANT_ONLY`、`input_kind=SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT`、`system_prompt=null`、`world_card=null`、`train_admitted=false`。
5. 输出到新建0700的Owner私有目录中：0600的两行实验性JSONL和0600的私有清单含源历史条数、输入字数、目标字数与字节SHA；只在受控私有目录内保留完整文本。SAFE输出仅计数与HOLD，无真实正文、ID、路径、哈希或旧模型评分。
6. **尚未验证**Qwen的真实chat template是否允许无system的消息格式、任何自动插入的模型System、token长度、标签掩码、Collator和世界约束充足性。这个工具不加载tokenizer，不输出可交给GPU执行的正式准入数据集。

## Owner Mac执行：复用之前已有源文件，不重跑审核

先同步固定分支新HEAD；确认Owner工作树干净且没有其它agent在其上编辑。执行：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
WORK="$HOME/workspace/storyforge-r60-4router-review"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
# 从本交接最终确认的固定完整SHA选择，禁止跟随浮动分支覆盖其它agent更改
git -C "$WORK" status --short
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_common2_sft_experimental_cpu.py
```

使用Owner已核实的`EXPAND_DIR`（就是已成功进行Wave40的真实展开目录）、Common2盲审原目录、已签PASS的裁决文件和已恢复历史目录。**这几份私有位置在本Agent运行时不可见，因此不凭空填入虚假的文件路径。** 命令示例：

```bash
BASE="$HOME/.local/share/storyforge/r60/private"
EXPAND_DIR="/已核实的Real1000冻结展开目录"
BLIND_DIR="/已核实的Common2独立盲审包目录"
DECISIONS="/已核实的Common2独立PASS决策JSON文件"
RECOVERY_DIR="$BASE/r60-real1000-qd20-common2-supabase-recovery-v1"
OUT_DIR="$BASE/r60-real1000-common2-sft-experimental11-v1"
test -f "$EXPAND_DIR/R60_EXPAND_CONFIG_PRIVATE.json"
test -f "$BLIND_DIR/R60_QD20_COMMON2_BLIND_PRIVATE.json"
test -f "$DECISIONS"
test -f "$RECOVERY_DIR/R60_QD20_COMMON2_SUPABASE_RECOVERY_PRIVATE.json"
test ! -e "$OUT_DIR"
python3 experiments/r58_quality/r60_real1000_common2_sft_experimental_cpu.py \
  --expand-dir "$EXPAND_DIR" --blind-dir "$BLIND_DIR" \
  --decisions "$DECISIONS" --recovery-dir "$RECOVERY_DIR" \
  --output-dir "$OUT_DIR" --window 11
```

预期`COMMON2_SFT_EXPERIMENTAL_2_READY__TRAIN_HOLD`。如果HOLD，保持Owner所有原始私有文件不变；反馈SAFE状态即可，不要粘贴模型训练目标/用户消息。

## 下一步真正要验证

1. 先根据这两个源绑定样本确认角色/上下文是否满足故事叙述条件；有世界设定缺失的样本不擅自补设定。对无system/no-world策略做明确的**实验假设**，不能当作当时真实提示词事实。
2. 选择已经冻结的Qwen tokenizer revision与chat template，在Mac本地CPU/离线环境对完整输入和最后目标计算真实token长度；冻结一版可复现的(max_length)与截断策略，截断不能切开目标或更改历史事实。
3. 仅在CPU调用实际ms-swift collator，验证仅最后assistant消息参与监督、历史user和assistant均被mask、特殊结束符及长度正确。
4. 从Owner已冻结的全部R50保护源ID中做全面故事/消息/会话重叠检查（不能仅依靠五个已知story）。**即使文本与模型格式都PASS，完整R50未验证时两条仍不得进入正式train。**
5. 两条样本全过技术和隔离门禁后，才扩大Real1000中的高质量候选审核/构造；是否启动GPU及数据冻结另行由Owner批准。

**不可混淆**：质量PASS 2/2；实验性SFT构造待真实Owner运行；正式训练准入0/2；Wave40盲审待执行。
