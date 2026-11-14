# R60 REAL1000 快速筛选执行书：API双审覆盖优先（2026-11-13）

> Owner明示：接受不完美方案，优先尽快推进冻结1000条筛选。本文件是**方案B的快速执行变体**：保留每条A/B审核、证据链及技术HOLD，不再阻塞于HF Qwen3-32B/GLM4-32B工程调试。本文件不代表已有1000条实际模型审核，也不准许将内容/技术HOLD自动入训。

## 选择依据与局限

使用历史已实际验证的 `qwen3.7-flash`（阿里云百炼）+ `deepseek-flash`（官方API）：QD20有效率分别18/20、16/20；不外推为全量有效率或准确率。此二者**不是**原HF Stage固定的`Qwen3-32B`+`GLM-4-32B`，不能将新模型回执写入旧HF Stage或冒充其审稿。与早期Claude+DeepSeek Pilot5也不同，须创建**全新可追溯的私有Quality批次目录**。严禁覆盖原本5份/v2回执。

该方案复用`experiments/r58_quality/r60_real_quality_batch.py`（1000条源验证、最多每次25、不可覆盖case回执、双模型单次请求、错误隔离、inspect SAFE）与`r60_real_ai_dual_review.py`、同一`r60_real_private_batch.FLOORS`。不新建第三Reviewer，不降低门槛。

实际历史 QD20 endpoint/模型名：Qwen `https://dashscope.aliyuncs.com/compatible-mode/v1` + `qwen3.7-flash`；DeepSeek `https://api.deepseek.com` + `deepseek-flash`。须由Owner用现有凭据与当前模型可用性复核；如果响应model和期望不一致或当前服务端协议变更，停机，不能把别名当模型身份证据。

**兼容性注意**：现有私有Quality Batch runner固化 A环境变量 `R60_CLAUDE_KEY`、B `R60_DEEPSEEK_KEY`，虽然模型字段可以是其它模型。为最快复用，不改历史Runner、不改冻结v1：在`advance`单个子进程环境中把`DASHSCOPE_API_KEY`短暂映射给`R60_CLAUDE_KEY`；这是已审查的临时**变量别名**，**不调用Claude**，不在日志打印任何key，也不将凭据写入GitHub或配置。待全量筛选后再做通用变量重构，不在本次阻塞。

## 目标与执行节奏

- 1000条结构PASS、与旧HF Stage身份PASS的Owner SAFE已取得，不重新跑筛选和旧Stage。
- 使用全新 `r60-quality-fast1000-api-v1` 私有目录，`init`只允许一次。
- 第1次只运行25条，明确检验Qwen/DeepSeek**当前**协议/配额和技术失败情况；再在每25条批末汇总SAFE。为了尽快完成，在首批有效且Owner选择继续时可以逐25条推进剩余975，不再以单条文学分歧停止扩批。
- 软异常只记录`MODEL_JSON_INVALID`、分数/严重旗标不一致等技术HOLD，不无限重试。不对轻微分歧额外请求第三模型。
- 硬停：冻结源SHA不一致、配置/回执不一致、输出被覆盖、两服务同时不可用、无效响应明显大面积发生、泄漏密钥/小说正文、费用预算达限。
- 此处“覆盖1000”表示`cases_reviewed=1000`、每例有A/B尝试及不可覆盖回执；不意味着`complete_pairs=1000`，更不意味着`quality_pass=1000`。
- 不使用`--owner-attest-independent-ai`，除非Owner实际完成各模型独立性核对；因此正式Quality PASS可能保持0，报告须另区分双审有效且双方PASS的临时候选和最终准入。

## Owner Mac 命令（先25条）

~~~bash
set -euo pipefail
set +x
umask 077
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
test "$(git branch --show-current)" = "r60/common2-cpu2-owner"
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
SOURCE="$BASE/r60-expand-first-600"
OUT="$BASE/r60-quality-fast1000-api-v1"
: "${DASHSCOPE_API_KEY:?在当前私有终端预先设置Qwen API key}"
: "${DEEPSEEK_API_KEY:?在当前私有终端预先设置DeepSeek API key}"
test ! -e "$OUT"

"$PY" experiments/r58_quality/r60_real_quality_batch.py init \
  --expand-dir "$SOURCE" --output-dir "$OUT" \
  --endpoint-a "https://dashscope.aliyuncs.com/compatible-mode/v1" \
  --model-a "qwen3.7-flash" --protocol-a openai-chat \
  --endpoint-b "https://api.deepseek.com" \
  --model-b "deepseek-flash" --protocol-b deepseek-chat \
  --allow-remote-review --timeout 180

R60_CLAUDE_KEY="$DASHSCOPE_API_KEY" \
R60_DEEPSEEK_KEY="$DEEPSEEK_API_KEY" \
"$PY" experiments/r58_quality/r60_real_quality_batch.py advance \
  --output-dir "$OUT" --max-cases 25

"$PY" experiments/r58_quality/r60_real_quality_batch.py inspect \
  --output-dir "$OUT"
~~~

注意：`init`不检查凭据也不会发送私有正文；`advance`才会对外发送模型审核提示。现有`advance`是串行按案例调用两个API，对现有目录无需重新init。不要对旧`r60-quality-first-1000`运行此快速筛选配置。当前用户选择加速方案，但实际API用量/费用仍需Owner在运行时控制；外发范围为全量1000条可见3消息+目标正文（每例A/B各一次）。

## 首25验收，然后批量覆盖

首25的`inspect`必须返回`cases_reviewed=25`，模型请求错误不能全部被判为文学REJECT。预设工程止损（用于防灾，不是质量门槛）：25条中模型技术失败总数**超过20个槽位**就暂停、定位协议；如果两个provider同一案例都出现网络/服务级不可用，原Runner会在写该案前HOLD，原样保留可恢复进度。其它文学REJECT/HOLD不触发暂停。

确认首25正常且预算允许后，逐批推进。为避免40次手动操作，下面可选择在Owner Mac**前台**执行、保留每批SAFE并在任何返回非零时停止；不启动后台任务。

~~~bash
# 在上面的变量和API key仍在同一终端时使用；仅当首25已验收
for round in $(seq 2 40); do
  R60_CLAUDE_KEY="$DASHSCOPE_API_KEY" \
  R60_DEEPSEEK_KEY="$DEEPSEEK_API_KEY" \
    "$PY" experiments/r58_quality/r60_real_quality_batch.py advance \
      --output-dir "$OUT" --max-cases 25
  "$PY" experiments/r58_quality/r60_real_quality_batch.py inspect \
    --output-dir "$OUT"
done
~~~

该前台循环尚**没有内建**成本上限、技术HOLD占比自动停机或完整自动成本计算。因此不应在无人监管时使用；如需要全自动、成本硬上限，应单独增加守卫而非绕过现有回执不可覆盖保障。遇临时错误可停止并反馈SAFE，不删目录、不覆盖v1结果。

## 完成后的通用统计

已有`inspect`提供`candidate_total`、`cases_reviewed`、`quality_decisions`、`hold_reject_codes`、`model_attempt_hold_counts`。由于未自动认可Reviewer独立性，`quality_pass`不代表预备双PASS总量；任何进一步“提取训练候选”须从Owner-only回执读取并按原冻结六维/严重标记及精确证据核验后，在新的私有候选集单独汇总，**不得篡改已有回执或自动Gold晋升**。

当前保持`quality_v1_admitted=0`、`train_admitted=0`、`gpu_started=false`、`r50_complete_exclusion_verified=false`、`historical_system_snapshot_verified=false`、`world_isolation_verified=false`。


## 2026-11-13 Owner真实首25 SAFE：建议累计100，不重跑已完成样本

Owner提供的两份 `inspect` SAFE 完全相同：`QUALITY_BATCH_IN_PROGRESS__TRAIN_ADMISSION_HOLD`，`cases_reviewed=25`，`remaining_cases=975`，`quality_decisions={PASS:0,HOLD:24,REJECT:1}`，`quality_pass=0`，`reviewer_independence_attested_by_owner=false`，`train_admitted=0`。HOLD/REJECT原因：`INDEPENDENCE_NOT_ATTESTED=2`、`REVIEW_INCOMPLETE=9`、`TWO_INDEPENDENT_REVIEWS_REQUIRED=13`、`SEVERE_OR_REVIEWER_REJECT=1`，合计25。

**技术失败共15次/最多50审核槽位（30%）**：`MODEL_HTTP_400_HOLD=2`、`MODEL_JSON_INVALID=2`、`QUALITY_FLOOR_DECISION_INCONSISTENT=8`、`SEVERE_FLAG_DECISION_INCONSISTENT=3`。这15是模型**尝试槽位**计数，不是15条错误案例；其余35次不能仅凭SAFE证明质量正确。不要把`PASS=0`解释成只有0条值得训练，或把技术错误算文学REJECT。

按既定**每25条技术失败超过20槽位才停止**的工程门槛，本轮15/50未触发该止损，允许继续推进75条到累计100；若连续下一批出现两侧服务不可用/来源SHA改变/回执报错，应立即保留现有源、停止扩批。文学评分HOLD/REJECT不自动停机。

在同一Owner Mac终端恢复，**不要重新执行init，不删除/覆盖目录**；凭据通过现有私有环境加载：

~~~bash
set -euo pipefail
set +x
umask 077
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
OUT="$HOME/.local/share/storyforge/r60/private/r60-quality-fast1000-api-v1"
: "${DASHSCOPE_API_KEY:?Missing Qwen API key}"
: "${DEEPSEEK_API_KEY:?Missing DeepSeek API key}"
test -d "$OUT"
"$PY" experiments/r58_quality/r60_real_quality_batch.py inspect --output-dir "$OUT"
for pass in 1 2 3; do
  R60_CLAUDE_KEY="$DASHSCOPE_API_KEY" R60_DEEPSEEK_KEY="$DEEPSEEK_API_KEY" \
  "$PY" experiments/r58_quality/r60_real_quality_batch.py advance --output-dir "$OUT" --max-cases 25
  "$PY" experiments/r58_quality/r60_real_quality_batch.py inspect --output-dir "$OUT"
done
~~~

预期累计`cases_reviewed=100`、`remaining_cases=900`，但这不是预先宣称真实成功。**不要把随后975条交给无费用上限的后台循环**。如果Owner确认100条运行稳定，可以继续以25条前台批次推进、适时检查配额/余额并主动停止，不额外反复模型选型或对前25失败样本重复调用。

分流后续不能仅依赖汇总`quality_pass`，因为当前Reviewer独立性未Owner认证；需追加一个**只读**的原回执视图，报告两侧有效数量、有效双审完整对、双PASS但独立性HOLD等数量后，再决定是否做集中复核和训练候选提取。不能在没有真实语义来源证据前把双PASS提升为Gold。


## 2026-11-13 最新真实250 SAFE：持续HTTP401，必须先定位再续跑

Owner实测`cases_reviewed=250`、`remaining_cases=750`、`quality_decisions=HOLD239/REJECT11/PASS0`。前150无401，而新增100条恰有`MODEL_HTTP_401_HOLD=100`，同时`TWO_INDEPENDENT_REVIEWS_REQUIRED`从72增至172；强烈提示某一Reviewer凭证或服务端权限持续失效，而非文学质量下降。继续盲跑将产生更多不可覆盖的单侧回执。

新的**只读** `r60_real1000_reviewer_failure_side.py`验证原1000冻结来源、每条已提交回执、原SHA，然后在**只剩单个有效Reviewer**时推断失败方；如果两侧都失败，旧receipt没保存`attempt_holds`侧别，不作猜测。全部输出只有聚合SAFE，无私有正文、case ID、密钥、endpoint、单案哈希。无任何API请求。

**先执行本地侧别审计，绝不重新init或advance：**

~~~bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
OUT="$HOME/.local/share/storyforge/r60/private/r60-quality-fast1000-api-v1"
"$PY" experiments/r58_quality/r60_real1000_reviewer_failure_side.py \
  --output-dir "$OUT"
~~~

如有`REVIEWER_FAILURE_SIDE_AUDIT_PASS__NO_REQUEST`，根据`known_error_counts_by_side`里的HTTP401分布确认故障方。A=`qwen3.7-flash`，B=`deepseek-flash`。由于回执里未必能标明双失败时每个错误的侧别，`unassigned_error_counts`必须单列不可认领。

**再用现有合成探针验证，不发送任何原小说文本**。Owner端的`DASHSCOPE_API_KEY`和`DEEPSEEK_API_KEY`应在当前私有终端已设置。只针对401故障模型执行一次：

~~~bash
# Qwen侧A出现401时:
"$PY" experiments/r58_quality/r60_reviewer_protocol_probe.py \
  --endpoint https://dashscope.aliyuncs.com/compatible-mode/v1 \
  --model qwen3.7-flash --protocol openai-chat \
  --key-env DASHSCOPE_API_KEY --allow-remote-review --execute

# DeepSeek侧B出现401时（与Qwen二选一）:
"$PY" experiments/r58_quality/r60_reviewer_protocol_probe.py \
  --endpoint https://api.deepseek.com \
  --model deepseek-flash --protocol deepseek-chat \
  --key-env DEEPSEEK_API_KEY --allow-remote-review --execute
~~~

只有故障侧真实合成请求返回`REVIEWER_SYNTHETIC_API_PASS__NO_PRIVATE`才恢复真实1000池。修复密钥后，**当前250条回执仍不会自动补审**；后续先对新样本执行最多1批25条验证恢复，之后再推进剩余750条；第151–250条失败槽位留待版本化单侧补审，不覆写旧回执。

**注意**：此前“快速首25模型技术失败15/50”不含后续401；当前250条的模型失败共`16+100+5+75+8=204`个尝试槽位，其中100为明确的HTTP401。若401尚未解决，不继续付费审核新样本；若修复后需要重复某一侧输出，必须新建create-only补审空间并严格复用原case SHA和模型绑定。


## 2026-11-13 REAL1000 250条故障侧只读审计 PASS

Owner实测 `REVIEWER_FAILURE_SIDE_AUDIT_PASS__NO_REQUEST`：`cases_reviewed=250`、`both_valid=78`、`only_a_valid=37`、`only_b_valid=103`、`neither_valid=32`。因此A有115个有效侧结果、B有181个有效侧结果；140条仅一侧有效、32条两侧无有效结果。

按单侧已知回执定位：A(Qwen) `MODEL_HTTP_401_HOLD=76`、`MODEL_HTTP_400_HOLD=14`、`QUALITY_FLOOR_DECISION_INCONSISTENT=13`；B(DeepSeek) `MODEL_JSON_INVALID=4`、`QUALITY_FLOOR_DECISION_INCONSISTENT=30`、`SEVERE_FLAG_DECISION_INCONSISTENT=3`。32条两侧无效共含**未归属的401×24**、400×2、JSON×1、评分×32、严重×5，不能擅自分配给A/B。**可以确定A存在显著认证故障，不能断言全部100次401来自A。**

下一行动：**仅执行Qwen侧合成请求诊断一次**，采用现有 `experiments/r58_quality/r60_reviewer_protocol_probe.py --endpoint https://dashscope.aliyuncs.com/compatible-mode/v1 --model qwen3.7-flash --protocol openai-chat --key-env DASHSCOPE_API_KEY --allow-remote-review --execute`（Owner Mac, 无私有数据）。若`REVIEWER_SYNTHETIC_API_PASS__NO_PRIVATE`，则先对原目录仅新案例跑一批25条、核验新增401=0后继续。若401或其他非PASS，停机诊断密钥、权限或协议，不继续把失败写成不可覆盖回执。不对旧250条重跑；额外补审需create-only独立新版本。原Quality合同、训练准入与R50隔离仍HOLD。


## 2026-11-13 Qwen真实合成探针：HTTP已通过，质量决策一致性未通过

Owner回传 `REVIEWER_PROTOCOL_HOLD`/`QUALITY_FLOOR_DECISION_INCONSISTENT`，`model_requests=1`，`synthetic_only=true`，`private_source_accessed=false`。阅读冻结源码可确认 `r60_real_ai_dual_review.model_request` 只有在网络响应内容已解析为JSON且到达 `parse_model_response` 后才会抛此码；此次请求**没有返回HTTP401**，但`reviewer schema/decision` **没有通过完整质量合同**。不能报告为`REVIEWER_SYNTHETIC_API_PASS__NO_PRIVATE`，也不能视作Qwen所有真实后续请求都可用。

根据Owner“尽快覆盖1000、接受技术HOLD”的优先级，建议用现有原批次创建**仅5个新样本**的受限真实恢复验证，不重试251之前的任何旧样本、不重跑合成探针、不修改Rubric/自动Gold入训。条件是Owner愿意承担这5例最多10次远端审核尝试及费用。执行前后分别`inspect`，只观察**新增401**和有效双侧数量变化。如果出现任一新的401，立即停止；如无401且结果可继续，则每批25并在每批后统计新增认证错误和技术失败，避免重演151–250段的100次401。现有runner自身**不会因单侧401自动停**，因此不要直接运行长循环。

Owner Mac：

~~~bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
OUT="$HOME/.local/share/storyforge/r60/private/r60-quality-fast1000-api-v1"
: "${DASHSCOPE_API_KEY:?Missing Qwen key}"
: "${DEEPSEEK_API_KEY:?Missing DeepSeek key}"
"$PY" experiments/r58_quality/r60_real_quality_batch.py inspect --output-dir "$OUT"
R60_CLAUDE_KEY="$DASHSCOPE_API_KEY" R60_DEEPSEEK_KEY="$DEEPSEEK_API_KEY" \
  "$PY" experiments/r58_quality/r60_real_quality_batch.py advance --output-dir "$OUT" --max-cases 5
"$PY" experiments/r58_quality/r60_real_quality_batch.py inspect --output-dir "$OUT"
~~~

预期`cases_reviewed=255`（若成功推进），之前累计HTTP401为100。若本轮401超过100，不再执行任何真实`advance`，转入凭证/模型权限复查；若无新增401，恢复受控25条批量。新模型结果可能仍出现`QUALITY_FLOOR_DECISION_INCONSISTENT`，保持技术HOLD、不降低评分门槛。原250条失败槽位只能版本化补审，不能覆盖旧回执。


## 2026-11-13 REAL1000 255实际回执：401恢复测试失败，暂停任何advance

Owner两次回传同一SAFE：`cases_reviewed=255`，`MODEL_HTTP_401_HOLD=105`（此前250为100），`QUALITY_FLOOR_DECISION_INCONSISTENT=76`（此前75），`TWO_INDEPENDENT_REVIEWS_REQUIRED=177`（此前172），`HOLD244/REJECT11/PASS0`，剩余745。与此前合成Qwen`QUALITY_FLOOR_DECISION_INCONSISTENT`（未401）对比，只能证明合成请求到达过解析器，**不能宣布真实审核认证修复**。继续试用原`advance`将把认证故障不可逆地固定为单侧HOLD，因此停止调用。

接下来只运行零模型请求的故障归属及本机批次配置对照，**不要输出实际Endpoint/模型凭据/私有正文**：

~~~bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
OUT="$HOME/.local/share/storyforge/r60/private/r60-quality-fast1000-api-v1"

"$PY" experiments/r58_quality/r60_real1000_reviewer_failure_side.py --output-dir "$OUT"

"$PY" - "$OUT" <<'PY'
import importlib.util
import pathlib
import sys
root = pathlib.Path("experiments/r58_quality").resolve()
sys.path.insert(0, str(root))
import r60_real_quality_batch as batch
c = batch.validate_config(pathlib.Path(sys.argv[1]))
checks = {
    "qwen_endpoint_expected": c["endpoint_a"] == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    "qwen_model_expected": c["model_a"] == "qwen3.7-flash",
    "qwen_protocol_expected": c["protocol_a"] == "openai-chat",
    "deepseek_endpoint_expected": c["endpoint_b"] == "https://api.deepseek.com/chat/completions",
    "deepseek_model_expected": c["model_b"] == "deepseek-flash",
    "deepseek_protocol_expected": c["protocol_b"] == "deepseek-chat",
}
import json
print(json.dumps({"config_matches_expected": checks, "model_requests": 0, "private_values_emitted": False}, sort_keys=True))
PY
~~~

这将进一步明确是否为A侧新401（新增5个的错误归属可能在全部0有效的案中无法辨别），以及实际Batch冻结配置是否同合成探针一致。如配置吻合且A确实持续401，后续需直接在百炼平台检查Key所属工作空间、有效性和`qwen3.7-flash`可用性。B侧不得因A认证失败反复消耗费用。

**加速目标仍是完成1000条筛选，但不允许把745条全部标为认证失败来冒充实际质量筛选。** 如果A无法及时恢复，应明确切换为“B单侧快速筛选＋A补审的独立新路线”，先保留已存在255条原始证据；新路线需要额外新私有回执和定义单侧候选而非伪造双审。当前仍无Gold/训练准入。


## 2026-11-13 快速路线切换：前255保留，新增DeepSeek单侧256—1000

Owner只读审计`cases_reviewed=255`，`both_valid=78`、`only_a_valid=37`、`only_b_valid=107`、`neither_valid=33`。已知A/Qwen 401累计80，另25次双失败401未归属；双模型endpoint/model/protocol六项布尔检查全true。实际第251–255条又增加5次401，确认现有双模型Runner持续写入单侧HOLD，不能继续跑旧`advance`。

为满足“优先完成1000条筛选覆盖，接受不完美”而保留证据，新增`experiments/r58_quality/r60_real1000_deepseek_single.py`：
- 仅处理冻结1000条的**第256—1000条**，完全复用原`frozen_pool`、单模型`ai.model_request`、冻结六维/严重标记校验，始终使用DeepSeek官方Flash。
- `init`需要旧私有批次严格255条且source SHA/DeepSeek配置一致，创建独立`0700`目录；原255份文件原样保留。
- `advance`要求明确`--execute --allow-private-data-egress`、`DEEPSEEK_API_KEY`，每批最多25条；模型认证/服务故障在**写盘前HOLD**以便恢复，解析/评分不一致保存为`TECHNICAL_HOLD`，不做重试。
- 回执为0600不可覆盖、来源case身份+源哈希+不可改SHA，进度可`inspect`核验；技术HOLD、`PROVISIONAL_PASS`、`PROVISIONAL_HOLD`、`PROVISIONAL_REJECT`分开统计，**明确不是正式双审、Gold或训练准入**。
- 这里“已覆盖1000条”最后的含义是旧255条双模型尝试及新增745条DeepSeek单模型尝试，不表示1000个有效质量决定，也不表示缺失A/B审稿已经补全。旧255里的32+1两侧均失败仍需将来单独补审。

在Mac使用原本的R60 Owner工作树，注意不要重新启动旧双模型的`advance`：

~~~bash
set -euo pipefail
set +x
umask 077
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
test "$(git branch --show-current)" = "r60/common2-cpu2-owner"
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
OLD="$BASE/r60-quality-fast1000-api-v1"
NEW="$BASE/r60-quality-fast1000-deepseek-single-v1"
: "${DEEPSEEK_API_KEY:?Missing DeepSeek key}"
test ! -e "$NEW"

# 初始化只读旧255+独立新Stage；不调用模型
"$PY" experiments/r58_quality/r60_real1000_deepseek_single.py init \
  --old-dir "$OLD" --output-dir "$NEW"

# 首25单侧真实模型请求，由Owner明确执行
"$PY" experiments/r58_quality/r60_real1000_deepseek_single.py advance \
  --old-dir "$OLD" --output-dir "$NEW" --max-cases 25 \
  --execute --allow-private-data-egress

"$PY" experiments/r58_quality/r60_real1000_deepseek_single.py inspect \
  --old-dir "$OLD" --output-dir "$NEW"
~~~

首批成功时，`single_cases_reviewed=25`、`total_positions_attempted=280`、`remaining_single_cases=720`。如返回`SINGLE_REVIEW_HOLD`，立即暂停并保留所有输出，不删除重建。确认没有认证/服务故障及预算足够后，同一`advance --max-cases 25 --execute --allow-private-data-egress`分批续跑剩余720条；单批请求最多25次，且要观察服务费用/余额。不要在无自动预算保护时做无人监管循环。

合成回归详见同目录`test_r60_real1000_deepseek_single.py`；1000条真实数据只在Owner Mac读取，CI不会触达。


## 2026-11-14 REAL1000 V1审核1000/1000完成：只读补审优先级规划

Owner SAFE 确认 `QUALITY_BATCH_REVIEWED__TRAIN_ADMISSION_HOLD`，1000/1000次双侧审核尝试写入V1不可覆盖回执，`HOLD=872,REJECT=128,PASS=0`（独立性未认证门禁使正式PASS为0）。原因分布：`INDEPENDENCE_NOT_ATTESTED=159`、`REVIEW_INCOMPLETE=200`、`TWO_INDEPENDENT_REVIEWS_REQUIRED=513`、`SEVERE_OR_REVIEWER_REJECT=128`。缺失的模型审核槽位合计577，不等于577条不同样本。

Owner只读侧别 SAFE `REVIEWER_FAILURE_SIDE_AUDIT_PASS__NO_REQUEST`：`both_valid=487`、`only_a_valid=216`、`only_b_valid=233`、`neither_valid=64`，因此A/Qwen有效703次、B/DeepSeek有效720次。应补失败侧合计A297、B280，包括64条两侧均失败。此前失败侧未归属时，不能按原`attempt_holds`列表位置武断决定哪侧是哪种错误。

新只读规划器 `experiments/r58_quality/r60_real1000_v1_repair_plan.py`：基于冻结1000源`pool_sha256`和现有V1签名回执（先严格运行`batch.inspected_records`），按照以下**不更改六维门槛**的类别分组：`READY_DUAL_PASS_NEEDS_ATTESTATION`（预计159，需真实Owner独立性认证/事实来源审查，不能自动认定）；`SINGLE_PASS_REPAIR_FIRST`（有效一侧PASS且未触发严重标记和六维floor，优先补另一侧）；`DUAL_VALID_OTHER_REVIEW`（完整双侧但非双PASS/拒绝）；`SINGLE_OTHER_DEFER`、`SINGLE_REJECT_DEFER`；`EXISTING_REJECT_REVIEW`；`BOTH_MISSING_LOW_PRIORITY`。会在新的私有0700目录中写入唯一0600不可覆盖manifest；记录原case_key、source SHA、旧receipt SHA和缺失侧别，不含小说正文。仅输出汇总SAFE。此阶段**不发模型请求，不执行任何补审，不启动GPU/训练或准入**。

Owner Mac命令：

~~~bash
set -euo pipefail
set +x
umask 077
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
OLD="$BASE/r60-quality-fast1000-api-v1"
PLAN="$BASE/r60-real1000-v1-repair-plan-20261114"

# 无网络预检，验证1000个原始不可覆盖回执
"$PY" experiments/r58_quality/r60_real1000_v1_repair_plan.py \
  --old-dir "$OLD" --output-dir "$PLAN"

# 预检通过后，创建只读V1结果导出的新私有规划目录
"$PY" experiments/r58_quality/r60_real1000_v1_repair_plan.py \
  --old-dir "$OLD" --output-dir "$PLAN" --write-private-plan
~~~

预期第一条 `REPAIR_PLAN_PREFLIGHT_PASS__NO_FILES`，第二条 `REPAIR_PLAN_SAVED__NO_MODEL_REQUEST`。两条的 `missing_slots_total` 应为577、`missing_slots_by_side` 为`{"a":297,"b":280}`，`cases_total=1000`。规划输出的各优先级精确数量**以Owner Mac真实SAFE为准**，不能由此前aggregate伪造。只有在读出具体`SINGLE_PASS_REPAIR_FIRST`规模与真实ROI后，再决定下一版本的create-only selective replay；严禁重新运行V1`advance`或把原159条自动提拔为Gold。
