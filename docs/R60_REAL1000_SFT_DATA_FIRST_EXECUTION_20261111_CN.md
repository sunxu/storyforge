# StoryForge R60 — 真实1000条优质历史数据 → SFT 数据优先执行任务书（2026-11-11）

## 2026-11-11 P20 第2条 PASS 后：自动隔离质量冲突、继续批量（CPU 合成验证）

Owner 实测 `processed=2, model_reviewed=1, conflict_pending=1, remaining=18`：首条PASS低于冻结中文文笔门槛已隔离，第二条Claude审核有效PASS，训练准入依然0。原审核器每遇新的 `PROXY_PASS_BELOW_FLOOR_HOLD` 都会中断，需要手动将失败快照quarantine后再次开始，付费API调用效率低。

新版运行器针对**当次真实API返回**、且原冻结Rubric严格证实为 `QUALITY_FLOOR_DECISION_INCONSISTENT` 的**唯一可自动恢复质量冲突**，在进程内带原模型对象生成不可覆盖的私有 `R60_PILOT20_CONFLICT_{position}_PRIVATE.json`，保存原判定PASS、原六维原分值、原理由、冻结包哈希/模型ID、固定冲突码；不构造伪PASS、不改模型原评分、不改训练准入。若分数满足冻结标准则仍以原有有效回执格式保存。两者逐位互斥，自动推进 `processed` 至下一条。

其他技术故障（HTTP/超时/截断/非法JSON/模型字段异常/严重标志矛盾）仍**立即停止批次**；已完成的回执/隔离记录保持原样，不覆盖，不自动重试、不继续付费。原始HTTP回复仍仅按需在Owner本地独立私有诊断目录保留。历史首条手动隔离记录和第二条有效回执无须迁移、重评分或重复提交。

批次最大值仍是 `MAX_CASES_PER_CALL=5`，剩余18条可按 5/5/5/3 分段运行。先在原固定worktree更新到最新经过 CI 验证的提交、跑无费用测试及inspect；如果之前某条计费请求失败但模型响应存在私有快照，先考虑本地replay/quarantine，避免不必要的重复付费。**只有Owner明确继续允许新一轮真实样本外发/计费，才运行 `advance --execute --allow-private-data-egress`**。失败时根据SAFE原因码停止分析，不盲目对同一失败样本反复提交。

```bash
cd "$HOME/workspace/storyforge-r60-4router-review"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
REVIEW="experiments/r58_quality/r60_real1000_pilot20_local_review.py"
OUT="$HOME/.local/share/storyforge/r60/private/r60-real1000-pilot20-4router-v1"
python3 "$REVIEW" inspect --output-dir "$OUT"
# Owner另行许可真实外发与费用后，再分批执行：
# python3 "$REVIEW" advance --output-dir "$OUT" --max-cases 5 --execute --allow-private-data-egress
```


## 2026-11-11 第1条质量冲突隔离，不阻断后续19条（最新）

Owner的 `replay-snapshot --position 1 --confirm-snapshot-provenance` 实际返回 `PROXY_PASS_BELOW_FLOOR_HOLD`，与原模型`PASS`但`chinese_prose=3`低于冻结门槛4一致。**不得反复重发首条、修改模型评分、降低门槛、把技术HOLD计作REJECT或把原始PASS直接当作入训PASS。**

修复单一连续回执队列的首条阻塞：新增 CPU-only `quarantine-snapshot`（显式确认原快照就是当前位置的原模型响应），读取Owner现有私有快照，要求模型id吻合、stop结束、完整严格JSON、原结论PASS且原Rubric明确拒绝该结论因为分数门槛。创建不可覆盖的 `R60_PILOT20_CONFLICT_0001_PRIVATE.json`，只记录原模型意见/六维得分/失败原因及与原冻结数据绑定的哈希；此条作为**已处理但未合格的冲突样本**，只能等待后续质量裁决。保留原始FAIL快照与原始PASS、绝不改写成合格评分。工作流`processed=1, conflict_pending=1, model_reviewed=0, remaining=19, train_admitted=0`； `advance`改用 `processed` 继续第2条（仍须实际外发/费用许可），不再卡在第1条。原有效回执仍严格验证，允许原混合序列每个位置为一份有效评分或一份冲突记录、禁止重号及跳号，保证resume可靠。

固定worktree原地同步并无费用验证：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
WORK="$HOME/workspace/storyforge-r60-4router-review"
PIN="6046a595060718f00759a994f50ae5790ca1605b"
test -z "$(git -C "$WORK" status --porcelain)" || exit 42
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
git -C "$ROOT" cat-file -e "$PIN^{commit}"
git -C "$WORK" switch --detach "$PIN"
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
OUT="$HOME/.local/share/storyforge/r60/private/r60-real1000-pilot20-4router-v1"
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py inspect --output-dir "$OUT"
```

只有Owner核实原快照确实属于冻结第1条时才隔离（CPU、无网络）：

```bash
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py quarantine-snapshot \
  --output-dir "$OUT" --position 1 --confirm-snapshot-provenance
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py inspect --output-dir "$OUT"
```

验收 `processed=1, conflict_pending=1, model_reviewed=0, remaining=19`；后续可在Owner明确新一轮外发及费用许可后`advance --max-cases 1`从第2条开始。禁止在公开文档披露私人理由文本或导出私有回执。未独立裁决时依然不允许任何训练准入。


## 2026-11-11 最新结论：第1条模型PASS但低于冻结质量门槛，不允许自动恢复为PASS

Owner提供的首条4Router Claude-Opus-5.5原始快照确认：`finish_reason=stop`，模型以完整 `\`\`\`json` 围栏输出；严格格式剥离后原始判断 `decision=PASS`，六维分值中 `chinese_prose=3`。但冻结的 `r60_real_private_batch.FLOORS["chinese_prose"]=4`。**因此模型结论与现有准入规则矛盾**，不能直接把快照恢复为有效PASS，也不能把3分偷偷改为4分。这个冲突是质量审查需要解决的问题，不是网络/JSON故障。

已保留对整块JSON围栏的严格剥离及CPU离线快照重放支持，但增加专门 SAFE 原因码 `PROXY_PASS_BELOW_FLOOR_HOLD`、`PROXY_SEVERE_FLAG_CONFLICT_HOLD`。尝试离线重放此快照将产生前者，不会写正式模型评分回执，`model_reviewed=0`，`quality_v1_admitted=0`，`train_admitted=0`。在明确的质量裁决机制确定应如何标注该样本前，不再为同一条重复付费模型请求，不降低现行分数门槛，不伪造模型判断，也不把技术失败计为REJECT。

诊断快照中有私有文学正文。不要复制到GitHub Issues或公开日志；主线任务书只记录固定SAFE类别与无敏感分数，不记录模型原始长篇理由。Owner若需核对，使用现有 `~/workspace/storyforge-r60-4router-review` worktree原地同步，并运行无费用的 `pytest`、`inspect`；不得重新初始化或创建worktree。


## 2026-11-11 4Router 首条响应已定位：完整 JSON 围栏，CPU 离线恢复

Owner 在现有私有诊断快照中确认：`finish_reason=stop`、`completion_tokens=1754`、正文1037字符，**以独立完整的 \`\`\`json 代码围栏包装原本有效JSON**。此前解析器直接 `json.loads(content)`，因第1字符为反引号而返回 `PROXY_MODEL_JSON_HOLD`。该问题是**格式包装**，不是模型审核失败；已有付费模型结果可以尝试本机离线恢复，无需再次调用API。

本次只允许剥离**整个正文严格匹配**的 `\`\`\`json<换行>JSON正文<换行>\`\`\``（允许首尾空白、JSON大写标签）；不允许扫描任意第一对花括号、允许额外解释文字、修补非法JSON、或者绕过六维 Rubric 检查。只有剥离后 `json.loads` 与原 `reviewer.parse_model_response` 均通过，才可能恢复 advisory 回执。新增 CPU-only `replay-snapshot` 模式，要求操作人显式确认 **snapshot确实来自当前冻结packet对应位置**（原始HTTP响应没有原输入hash，不可独立密码学核验该对应关系）；对模型 ID、当前packet文件hash、位置连续性及已有回执不可覆盖做保护；仅以本机私有快照产生既有格式的 create-only private receipt，不调用4Router，不产生API费用。恢复结果仍是 **模型建议评分而非独立质检/训练准入**，`quality_v1_admitted=0`、`train_admitted=0`。

在唯一固定 `~/workspace/storyforge-r60-4router-review` worktree 且工作区干净时原地同步代码：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
WORK="$HOME/workspace/storyforge-r60-4router-review"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
test -z "$(git -C "$WORK" status --porcelain)" || exit 42
git -C "$WORK" switch --detach origin/r60/p4-generation-eval-framework
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
OUT="$HOME/.local/share/storyforge/r60/private/r60-real1000-pilot20-4router-v1"
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py inspect --output-dir "$OUT"
```

若操作人能确认本地`R60_PILOT20_FAILED_0001_PRIVATE.json`就是对应第1条同一冻结packet和本次Claude调用的失败快照，可自行在Mac执行本地无费用恢复，**不要再次发送模型请求**：

```bash
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py replay-snapshot \
  --output-dir "$OUT" --position 1 --confirm-snapshot-provenance
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py inspect --output-dir "$OUT"
```

成功标准`model_reviewed=1, remaining=19`；若`PROXY_RUBRIC_SCHEMA_HOLD`仍出现，说明不是仅代码围栏问题，保持快照原样，分析评分字段，不要放宽Rubric或伪造PASS。真实模型内容和诊断快照不上传GitHub；不要在公开日志/聊天里粘贴模型的长篇隐私评语。


## 2026-11-11 4Router 真实首条 HTTP 200 后 Schema HOLD：离线快照诊断修复

Owner 使用已验证的 `https://4router.ai/v1/chat/completions`、8192-token预算，实际首条 `advance` 返回 `PROXY_RESPONSE_SCHEMA_HOLD`；`inspect` 仍 0/20、无有效评分。这是响应解析/字段审核技术失败，**不能标记案例为REJECT**。此前合成同协议案例曾 HTTP200、`finish_reason=stop`、1402 completion tokens、Rubric_VALID，表明格式并非普遍失效。本次HTTP200响应正文**当时未存档，不能无费用追溯原因**。

已修正审核器：细分 `PROXY_ENVELOPE_JSON_HOLD`（非JSON外壳）、`PROXY_ENVELOPE_STRUCTURE_HOLD`、`PROXY_CONTENT_STRUCTURE_HOLD`、`PROXY_MODEL_JSON_HOLD`（模型正文非JSON，Markdown围栏也仍属于无效JSON）、`PROXY_RUBRIC_SCHEMA_HOLD`（JSON可解析但未满足冻结Rubric），保留 `PROXY_TRUNCATED_HOLD` 和 `PROXY_EMPTY_HOLD`。只有严格通过原Rubric才写正式评分回执。模型返回但未通过解析时，新增仅在本机Owner私有根下、创建后不覆盖的原始响应快照（`$HOME/.local/share/storyforge/r60/private/r60-real1000-pilot20-4router-v1-response-diagnostics-v1/R60_PILOT20_FAILED_0001_PRIVATE.json`），限原本HTTP响应120000字节；**不能上传、粘贴、打印或提交此私有文件**。用CPU离线检查快照结构来修复，不依赖反复付费调用。由于原20条output目录有严格外来文件禁入规则，诊断快照保存在**同级独立私有目录**，不会破坏原`inspect`。

执行固定worktree无费用验证：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
WORK="$HOME/workspace/storyforge-r60-4router-review"
PIN="b97ff44798484bd22a4d603026ee0e89924ef631"
test -z "$(git -C "$WORK" status --porcelain)" || exit 42
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
git -C "$ROOT" cat-file -e "$PIN^{commit}"
git -C "$WORK" switch --detach "$PIN"
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py inspect \
 --output-dir "$HOME/.local/share/storyforge/r60/private/r60-real1000-pilot20-4router-v1"
```

下一次真实`advance --max-cases 1`须Owner重新确认私有案例外发和费用；如果再次发生Schema HOLD，记录其细分类别并在Owner Mac上私密离线分析新快照。**不可因为0份成功评分推断之前请求未外发或未计费。** 目前不启动GPU、数据库或训练，不新增worktree，不重新初始化。 


## 2026-11-11 4Router 首条真实审核返回 length — 输出预算修复（最新）

Owner 已将现有审核配置改为实测可用 `https://4router.ai/v1/chat/completions`，经 `inspect` 验证原私有20条审阅包配置可读；真实 `advance --max-cases 1` 返回 `PROXY_TRUNCATED_HOLD`，`model_reviewed=0`、`quality_v1_admitted=0`，原因是模型回复 `finish_reason=length`。这证明请求至少已获模型响应，不是初始HTTP断连；**可能已经发生私有数据外发及API计费**，不能按 `model_reviewed=0` 推断无费用或无外发。

已只修改 `r60_real1000_pilot20_local_review.py` 的 `REVIEW_MAX_TOKENS` 常量，从1600提升至8192；顶层 `system`、用户消息、评分Rubric、严格JSON输出验证、私有回执路径与签名、冻结样本均不改变。保留 `PROXY_TRUNCATED_HOLD` 为技术失败，绝不等同文学质量 `REJECT`。补充合成测试检查8192预算和截断安全处置；代码提交后先在**现有唯一固定worktree**原地同步并运行CPU测试。无需新建worktree、无需重建/覆盖配置或审阅包、无需清理任何回执。

```bash
set -euo pipefail
WORK="$HOME/workspace/storyforge-r60-4router-review"
ROOT="$HOME/workspace/storyforge"
git -C "$WORK" status --short
test -z "$(git -C "$WORK" status --porcelain)" || { echo "DIRTY_WORKTREE_HOLD"; exit 42; }
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
git -C "$WORK" switch --detach origin/r60/p4-generation-eval-framework
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py inspect \
  --output-dir "$HOME/.local/share/storyforge/r60/private/r60-real1000-pilot20-4router-v1"
```

如再审核真实第1条，必须由Owner明确批准本次再次外发及费用后执行 `advance --max-cases 1 --execute --allow-private-data-egress`；若仍length则暂停并研究思考预算/响应格式，不要无上限增加费用。模型生成未完成不写评分回执，阶段准入仍0。


## 2026-11-11 4Router 细分错误码 + 固定工作树（最新执行规则）

用户确认此次问题**与代理无关**，禁止因推测代理而继续改变联网行为。最新审核器只修改诊断：保留原显式无代理的联网设置，针对 HTTP 数字状态（400/401/403/404/429/5xx）、已知4Router/Claude错误`type/code`（严格有限白名单映射）、DNS、TLS证书校验、TLS握手、超时、拒绝连接、重置连接、无路由等输出细分的 `reason_code`。绝不输出原始HTTP错误正文、异常字符串、Key、URL或私有案例。合成回归覆盖类别；**原20条审阅包、旧配置和0份成功回执不覆盖、不重建**。

不再新建 worktree。Owner Mac 已有 worktree 清单显示 `/private/var/folders/fk/p_g8myrd27d3j7qp13zh_2gr0000gn/T/r60-4router-debug-kcZt62`（detached，旧e3e77759），把**这个现有worktree**迁移为唯一长期使用的 `/Users/keedle/workspace/storyforge-r60-4router-review`，前提是旧目录干净、目标不存在：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
OLD="/private/var/folders/fk/p_g8myrd27d3j7qp13zh_2gr0000gn/T/r60-4router-debug-kcZt62"
WORK="$HOME/workspace/storyforge-r60-4router-review"
test -d "$OLD"
test ! -e "$WORK"
test -z "$(git -C "$OLD" status --porcelain)"
git -C "$ROOT" worktree move "$OLD" "$WORK"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
git -C "$WORK" switch --detach origin/r60/p4-generation-eval-framework
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
```

如旧worktree有未提交变更，停止移动与删除，不要使用 `--force`、`git reset --hard`、`rm -rf`。同一目录今后直接原地 `git fetch` + `git switch --detach`（仅在干净且无其他agent写入时）；不新建工作树。

Owner 本次临时树可清理的仅以下明确列出的路径（**禁止删除**长期 `~/workspace/storyforge-*`、RolePlay、Gold Quality或本新固定树）：

```bash
ROOT="$HOME/workspace/storyforge"
T="/private/var/folders/fk/p_g8myrd27d3j7qp13zh_2gr0000gn/T"
for name in \
  r60-4router-6uBSEb r60-4router-bJOHtG \
  r60-calibration100-HWh8Jl r60-pilot20-ctAQkN \
  r60-qwen-cpu-8VgNz4 r60-real1000-RHId9x \
  r60-unified-2tai5e r60-unified-5Zm2gJ r60-unified-LFppup; do
  path="$T/$name"
  test -d "$path" || continue
  if [ -z "$(git -C "$path" status --porcelain)" ]; then
    git -C "$ROOT" worktree remove "$path"
    echo "REMOVED_CLEAN_WORKTREE=$name"
  else
    echo "SKIPPED_DIRTY_WORKTREE=$name"
  fi
done
git -C "$ROOT" worktree list
```

若旧debug树已成功迁移，它不应再出现在临时路径清理名单中。只执行 `git worktree remove`，不做 `prune --expire now`、`rm -rf` 或强制删除。清理前确认这些临时树没有正在运行的进程或其他Agent使用。

Owner 实际调用前（先不重发真实请求）在固定目录直接：`python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py inspect --output-dir "$HOME/.local/share/storyforge/r60/private/r60-real1000-pilot20-4router-v1"`，无费用。下一次只有Owner确认新一轮真实外发/费用后，才执行 `advance --max-cases 1 --execute --allow-private-data-egress`，回报具体 `stage=ADVANCE` + `reason_code`，以便辨认 HTTP 400 格式或 401 Key、429限速或 DNS/TLS 等；失败不自动重试。


## 2026-11-11 Owner 目录复用要求及4Router最新无费用回执

Owner 明确要求：**后续不要每次新建 worktree**；优先在已经存在、刚刚完成验收的同一工作目录中执行，不覆盖或重置并行Agent的工作树，也不为了每条SAFE回执重复`fetch`/`worktree add`/`init`。如果确实需要更新代码，只在确认目标工作目录无未提交改动、没有其他Agent占用后原地同步，或复用现有专用工作树；必须新建隔离目录时先说明原因。

Owner 最新`inspect`：`PILOT20_LOCAL_REVIEW_PARTIAL__OWNER_ADJUDICATION_PENDING`、`total_cases=20`、`model_reviewed=0`、`remaining=20`、`private_data_egress=false`，专用 `CLI_PROXY_API_KEY_PRESENT=yes`。说明本地配置、私有20条审阅包与绑定校验已通过，尚未向4Router发出真实评分请求，故此前无原因`HOLD`不能认作质量拒绝。**不重新init、不删除目录，也不重新抽样。**

在刚才成功`inspect`的工作目录下，且Owner明确确认本批新的20条正文外发及API费用后，直接执行：

```bash
set -euo pipefail
BASE="$HOME/.local/share/storyforge/r60/private"
REVIEW="experiments/r58_quality/r60_real1000_pilot20_local_review.py"
OUT="$BASE/r60-real1000-pilot20-4router-v1"
test -f "$REVIEW"
test -n "${CLI_PROXY_API_KEY:-}"
python3 "$REVIEW" advance --output-dir "$OUT" --max-cases 5 \
  --execute --allow-private-data-egress
python3 "$REVIEW" inspect --output-dir "$OUT"
```

首批5条仅视为模型ADVISORY，不自动训练准入。技术失败保留历史文件并回传SAFE `stage`/`reason_code`，勿盲目重复付费。未获单独批准不执行外发。


## 2026-11-11 4Router 技术 HOLD 定位修复（最新）

Owner 的 `PILOT20_LOCAL_REVIEW_HOLD` 回执没有包含子原因，**不能解释成模型 REJECT 或样本不合格**。经代码审查发现 `advance` 曾接受 `OPENAI_API_KEY` 作为存在性检查，但真正的HTTP请求只读取 `CLI_PROXY_API_KEY`；并且所有错误均折叠成无原因 HOLD。现已统一要求 `CLI_PROXY_API_KEY`，并增加严格白名单 `stage` / `reason_code`，绝不回显私有报错字符串、URL、Key、文本或返回正文。

最短无费用诊断：先用**新固定代码 PIN**运行合成测试；若此前 `init` 已创建目录，不再重复 `init`；直接运行 `inspect`（不调用API），即可区分配置/私有文件问题与后续 API 问题。若 `inspect` PASS，检查专用 Key 是否存在（仅打印yes/no，不回显Key）；如 `advance` 真实请求曾失败，新的SAFE会显示如 `PROXY_API_KEY_REQUIRED`、`PROXY_TRANSPORT_OR_HTTP_HOLD`、`PROXY_RESPONSE_SCHEMA_HOLD` 等。失败不自动重试已持久化位置，未经 Owner 明确确认不继续真实付费外发。

```bash
set -euo pipefail
BASE="$HOME/.local/share/storyforge/r60/private"
REVIEW="experiments/r58_quality/r60_real1000_pilot20_local_review.py"
OUT="$BASE/r60-real1000-pilot20-4router-v1"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
python3 "$REVIEW" inspect --output-dir "$OUT"
if [ -n "${CLI_PROXY_API_KEY:-}" ]; then echo "CLI_PROXY_API_KEY_PRESENT=yes"; else echo "CLI_PROXY_API_KEY_PRESENT=no"; fi
```

只有在 `inspect` 报 `PRIVATE_FILE_MISSING_HOLD`，并确认确实从未初始化时，才考虑原 `init`，不要因无原因HOLD就删除目录。原始20条审阅包和已有评分回执保持不变。



## 2026-11-11 P1 Pilot20 审核协议切换至 4Router Claude（最新）

已沿用 2026-11-09 在 R60 P2-A 上成功运行的 4Router/Claude Opus 5.5 协议：**顶层 `system`、`messages` 只含 `user`、不传 `temperature` 和 `response_format`**。复用现有 `r60_real_ai_dual_review.py` 的六维 Rubric 与严格 JSON 校验，当前20条审阅包、原始1000条冻结池和sample100均不改变。

`experiments/r58_quality/r60_real1000_pilot20_local_review.py` **保留历史文件名，但现只接受 `https://4router.ai` 及其HTTPS子域名**。Key **仅**从 Owner Mac 环境变量 `CLI_PROXY_API_KEY` 读取，不回退使用 `OPENAI_API_KEY`，避免把其他服务的凭据误发给4Router；Key不会写入配置文件或日志。申请调用时同时要求 `--execute --allow-private-data-egress`，否则拒绝调用。无明示批准不得调用，**此前 Development20 向 4Router 外发授权不覆盖本批新20条**。

待 Owner 明确确认向4Router外发这批20条正文及支付API费用后，用当前CI PASS PIN的独立worktree执行：

```bash
set -euo pipefail
umask 077
BASE="$HOME/.local/share/storyforge/r60/private"
REVIEW="experiments/r58_quality/r60_real1000_pilot20_local_review.py"
OUT="$BASE/r60-real1000-pilot20-4router-v1"
# 以下两项在当前 Owner Shell 中设置，禁止回显API Key：
: "${CLI_PROXY_API_KEY:?set the key in your private shell environment}"
: "${CLI_PROXY_BASE_URL:?set the previously verified 4Router HTTPS base URL}"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
test ! -e "$OUT"
python3 "$REVIEW" init \
  --packets-dir "$BASE/r60-real1000-pilot20-packets-v1" \
  --output-dir "$OUT" \
  --base-url "$CLI_PROXY_BASE_URL" --model claude-opus-5-5
# 付费 / 真实正文外发；必须由 Owner 单独批准后手动运行：
python3 "$REVIEW" advance --output-dir "$OUT" \
  --max-cases 5 --execute --allow-private-data-egress
python3 "$REVIEW" inspect --output-dir "$OUT"
```

`init` 不调用API，只持久化受约束的endpoint、模型、输入文件SHA；`advance` 最多5条，单条成功即创建不可覆盖0600回执，失败直接HOLD，不自动重试、不会记成质量REJECT；`inspect` 不外发，只统计ADVISORY PASS/HOLD/REJECT和严重标记。若5条全REJECT或严重标记异常高，先核验原因，不自动扩大15条。远程API的外发事实与本地GPU/HF GPU不同；代码不提交任何HF Job。即使模型报告PASS，正式训练准入仍为0。

**下文旧 localhost / Ollama 执行片段已被本节替代，不要用旧参数 `--endpoint` / `--json-mode`。**


## 2026-11-11 首批20条审阅包 Owner 验收 PASS，开始单模型试点

Owner Mac 对 `b6b25fb8c7a8a7db62db24375f323d23c63edabe` 报告：`4 passed in 0.06s`、`PILOT20_REVIEW_PACKETS_READY__NO_REVIEWS`、`cases_prepared=20`、`sample100_verified=true`、长度配额11/8/1；原始私有审阅包 `r60-real1000-pilot20-packets-v1` 已创建，尚无质量评分。

**下一步不再建新的冻结池或抽样包**。新增唯一薄适配 `r60_real1000_pilot20_local_review.py`，复用既有 `r60_real_ai_dual_review` 六维 Rubric/JSON 验证/OpenAI-compatible API；只允许 Owner Mac 的 localhost 服务，以最多5条/调用逐条审核，并在独立私有目录生成 create-only 的评分/理由回执。原始模型的 `PASS/HOLD/REJECT` 明确作为 *advisory*，不自动成为真实质量 PASS 或训练准入；需要独立参考对严重标记及争议做实质语义复核。失败中断后从已持久化的连续编号继续，不会重复已成功的请求。

Owner 确认自己本机已安装/运行可用 OpenAI-compatible 审核模型后运行如下命令（替换实际 `MODEL`，并根据实际本地服务填写 `ENDPOINT`）。这些命令会对真实私有20条逐条发起**本机模型推理**，可能占用 Mac CPU/GPU，但不提交远端 HF GPU Job：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
PIN="$(git -C "$ROOT" rev-parse origin/r60/p4-generation-eval-framework)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/r60-review20-XXXXXX")"
git -C "$ROOT" worktree add --detach "$WORK" "$PIN"
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
MODEL="替换为本机实际可用模型名称"
ENDPOINT="http://127.0.0.1:11434/v1"
OUT="$BASE/r60-real1000-pilot20-local-review-v1"
test ! -e "$OUT"
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py init \
  --packets-dir "$BASE/r60-real1000-pilot20-packets-v1" \
  --output-dir "$OUT" --endpoint "$ENDPOINT" --model "$MODEL" --json-mode
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py advance \
  --output-dir "$OUT" --max-cases 5
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py inspect \
  --output-dir "$OUT"
```

首轮五条审核后检查 `model_reviewed=5`、`model_decisions_advisory`、`model_severe_flag_counts_advisory`；若全REJECT并伴严重标记，立即对少数样本做独立复核，**不要直接继续15条**。若质量输出可靠，再执行三次 `advance --max-cases 5`。新脚本仅接受本地 `127.0.0.1/localhost/::1` 接口；不自动上传小说内容到第三方远程 API。训练准入保持0。


## 2026-11-11 P1 真实100条抽样 PASS → 20条小批质量审核包

Owner CPU `4 passed in 0.05s`，`CALIBRATION_SAMPLE100_READY__NO_REVIEWS`，抽样100/100个不同故事，目标字数层55/38/7，私有目录 `$HOME/.local/share/storyforge/r60/private/r60-real1000-calibration100-v1` 已创建。**P1 抽样 PASS，不代表任何质量审查完成**。

为避免再次因复杂GPU Reviewer耽误主线，新建 `r60_real1000_pilot20_packets_cpu.py`，对现有100条私有位置清单执行**全1000来源冻结摘要验签 + 按池指纹重新计算 sample100**，然后固定抽20条（11/8/1，仍每故事独立）。只在新的 Owner 私有目录创建一份含目标前三条历史与助手目标正文的审阅包；所有原文仅写本地0600文件，不能上传GitHub/CI或打印到对话。此时无AI审核调用、无训练准入。

Owner Mac 在 CI 合格的固定 PIN 上执行：
```bash
set -euo pipefail
umask 077
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
PIN="$(git -C "$ROOT" rev-parse origin/r60/p4-generation-eval-framework)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/r60-pilot20-cpu-XXXXXX")"
git -C "$ROOT" worktree add --detach "$WORK" "$PIN"
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_pilot20_packets_cpu.py
test ! -e "$BASE/r60-real1000-pilot20-packets-v1"
python3 experiments/r58_quality/r60_real1000_pilot20_packets_cpu.py \
  --expand-dir "$BASE/r60-expand-first-600" \
  --sample-dir "$BASE/r60-real1000-calibration100-v1" \
  --output-dir "$BASE/r60-real1000-pilot20-packets-v1"
```
SAFE 预期 `PILOT20_REVIEW_PACKETS_READY__NO_REVIEWS`，20条、层配额11/8/1。下一步用已可用的AI/OpenAI-compatible单主审核器依六维评分+严重证据进行20条**真实**审核，再抽查争议误判。20条工具完成 != 质量评审完成；未经独立参考，不报告误拒率。任何API审核费用/数据外传需另行确认。


## 2026-11-11 P1 分层校准100 真实抽样验收（覆盖下文 P1 抽样待执行文字）

Owner Mac 在 `1b177eb77637c2e2b15def4272cc546c1665e6c3` 实测：4个CPU合成测试 PASS；`CALIBRATION_SAMPLE100_READY__NO_REVIEWS`，来自 **100个不同故事**，目标字数层55/38/7；`database_accessed=false`、`gpu_started=false`、`private_values_emitted=false`，质量审核与训练准入均为0。Owner 私有位置清单已创建于 `$HOME/.local/share/storyforge/r60/private/r60-real1000-calibration100-v1`，不可覆盖或重新抽样。

**P1 抽样子项 PASS**；后续应该从固定100个位置中小批评审，而不是直接对整个1000条再次发起强制双模型GPU审核。先准备20条试点的私有、只读审阅包，按长度比例11/8/1，从100条已冻结抽样中确定性取样，开展单主审核器的真实评分与独立误判复核。只有实质评审结果才能计入质量进度。


## 2026-11-11 Owner P0 真实验收完成（覆盖下文 P0 待执行的历史说明）

Owner Mac 已对冻结 `r60-expand-first-600` 执行原生 `inspect` 与新 CPU 画像，真实 SAFE：
- 合成单测 `6 passed in 0.04s`；
- `EXPANSION_TARGET_REACHED__NOT_ADMITTED`，6种子 +994扩容=1000、20页、扫描400故事；
- `REAL1000_TECHNICAL_PROFILE_PASS__QUALITY_PENDING`，`cases_verified=1000`、`distinct_stories=285`、`max_cases_per_story=4`、三消息链和持久化目标各1000；
- 目标回复长度分布：300–499字545条、500–999字380条、1000–1500字75条；
- 历史实际System、世界组件、R50排除均有1000条状态未核证；这是后续训练前证据项，不应重新当成质量审核硬阻塞；
- `quality_review_performed=false`、`quality_pass=0`、`train_admitted=0`，无数据库访问或 GPU。

**因此 P0=PASS，下一项直接开始 P1质量校准抽样，不再重拉DB或 Tokenizer。**

新增 `r60_real1000_calibration_sample_cpu.py`：调用既有 `frozen_pool` 重新只读验签后，从1000条中按冻结池指纹+case_key确定性选100条，长度层配额55（300–499）/38（500–999）/7（1000–1500），每故事仅1条；只在Owner Mac新私有0700目录保存原始位置+长度层，不复制或公开原文/故事ID，公开输出仅SAFE计数。若任一配额无法满足故事唯一性则HOLD，不降低配额或自动覆盖历史抽样。

Owner Mac 下一命令（仅 CPU、无模型审核调用）：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BRANCH="r60/p4-generation-eval-framework"
BASE="$HOME/.local/share/storyforge/r60/private"
EXPAND="$BASE/r60-expand-first-600"
SAMPLE="$BASE/r60-real1000-calibration100-v1"
git -C "$ROOT" fetch origin "$BRANCH"
PIN="$(git -C "$ROOT" rev-parse "origin/$BRANCH")"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/r60-calibration100-XXXXXX")"
git -C "$ROOT" worktree add --detach "$WORK" "$PIN"
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_calibration_sample_cpu.py
test ! -e "$SAMPLE"
python3 experiments/r58_quality/r60_real1000_calibration_sample_cpu.py \
  --expand-dir "$EXPAND" --output-dir "$SAMPLE"
```

预期 `CALIBRATION_SAMPLE100_READY__NO_REVIEWS`，`sampled_cases=100`，`distinct_stories=100`，层配额55/38/7。**这只是可重复的独立抽样，不是100条质量已经 PASS。**


> **当前优先级入口；替代同日 GLM/Qwen 全量调试继续扩大的待办。** 单 Agent 负责 `r60/p4-generation-eval-framework`。本任务书只授权 GitHub 代码/文档、CPU-only 只读诊断；**不授权新的远端付费任务、GPU 推理、训练、数据库更改、PR 合并或正式训练准入**。

## 1. 目标与当前事实

目标是把已冻结的真实互动小说历史候选，尽早转换为经可证伪质量筛选的**首批训练候选**，继而做世界/历史/评测隔离、CPU Tokenizer/Collator、训练前审查。禁止以完成 GLM/Qwen 排障作为数据准备的前置条件。

已获得的历史 Owner SAFE：`EXPANSION_TARGET_REACHED__NOT_ADMITTED`，6条种子 + 994条新候选 = **准确1000条**；共20页、扫描400个故事。候选已保存在 Owner Mac `$HOME/.local/share/storyforge/r60/private/r60-expand-first-600`，采集输入为每案目标前3条实际 DB 消息（user/assistant/user）+ assistant 目标；不是完整多轮历史或实际发送的系统提示词。阶段性结构筛选条件为原始 `r60_real_expand_private.py` SQL 的**已完成 assistant、有效邻接角色链、目标长度300–1500、前序 user/assistant 长度边界、无已标记编辑或解析告警、非分叉根会话、每世界不超过4候选**等；这是**采集技术预筛**，并不证明高质量、长上下文完整、真实 System、世界卡或入训资格。

既有 A/B 各1000/1000的 CPU tokenizer 预检及 Owner crosswalk 验证已做；**不重新下载/导出、采样、CPU tokenizer，除非输入配置本身改变**。现有 `r60_real_quality_batch.frozen_pool` 可用原始页/seed、SHA、重复项、结构、Prompt 边界严格只读验证整池。既有 `r60_hf_quality_adapter.py prepare` 已在 Owner 实测1000 staged，`audit` 显示双模型审核0/1000，不能冒称已经审核完毕。

工程对照：GLM 全25份 Snapshot + CPU Replay 完成，模型原始25个 `decision=REJECT`；不是人工真值，剩余8个引用失败与质量区分。Qwen 前6份验签，第7条异常；在得到样本准入增益证据前，不继续为两者付费。GLM/Qwen 已有工程资产保留，不丢弃。

## 2. 立即执行：Owner 冻结池 CPU 状态检查（零 GPU）

使用当前单 Agent 分支的固定 HEAD + 既有工具检查（不改变原20页或种子，不重新访问数据库）：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
EXPAND="$BASE/r60-expand-first-600"
PIN="$(git -C "$ROOT" rev-parse origin/r60/p4-generation-eval-framework)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/r60-real1000-cpu-XXXXXX")"
git -C "$ROOT" worktree add --detach "$WORK" "$PIN"
cd "$WORK"
python3 experiments/r58_quality/r60_real_expand_private.py inspect --output-dir "$EXPAND"
python3 experiments/r58_quality/r60_real1000_technical_profile_cpu.py --expand-dir "$EXPAND"
```

只有当 `EXPANSION_TARGET_REACHED__NOT_ADMITTED` 且新 `REAL1000_TECHNICAL_PROFILE_PASS__QUALITY_PENDING`、`cases_verified=1000` 均收到，才视为**冻结候选池技术结构已核验**。若旧实际私有目录已迁移，Owner 用真实目录代入，不通过复制/覆盖原页伪造修复。脚本 SAFE 只显示结构性计数，无正文、ID、哈希，不生成正式准入标签。

## 3. 质量校准：先分层100条，不重启三模型批量

从技术核验通过的1000条中，在 Owner 私有工作区构造**故事分层、长度/复杂度分层的约100条校准子集**。与已冻结 Gold72 的 Development 部分和 Owner v2.1 Rubric 可对齐的才作为校准参考，Locked20、Severe10、R50 保留为评测/回归，不向待校准模型暴露答案。*不能直接把不同来源的 Gold 标签按“第n条”位置匹配这1000条；先用 Owner crosswalk/来源严格匹配，确无匹配则独立新裁决。*

质量判定核心：中文文笔、人物一致、NPC主动性、玩家自主权、局部规则/事实、叙事连续性。严重项必须有**明确支持的语义证据**；引文格式失败与质量不合格独立记录。用已经可用的单主模型/API 对校准样本评分，抽查误拒/漏拒；无法验证严重标记时 HOLD，不直接批量淘汰。若已有 Owner/人工参考，优先复用；不因为某模型25条全部 REJECT 就推断所有候选不合格。

**校准停止条件**：100条抽样内没有经过独立参考验证的稳定误判指标时，不扩大至1000条全量模型审核；改为受控 Owner 案例复核/简化审核合同。不要重复升级 Reviewer 框架来代替判断。

## 4. 第一批训练候选（先50–100，不等待1000条全部完审）

只从达到质量准入评审条件的实例中生成 `TRAIN_CANDIDATES_PRIVATE`（不是 TRAIN_ADMITTED），保留输入页指纹、来源与目标前历史链、原始回复 SHA、审核版本/证据以及拒绝/HOLD 的独立原因。来源 ID 与目标摘要仅用于技术追溯、去重和历史链关联；本轮按 Owner 已明确简化的审核范围，**不把来源权利、隐私、授权证据作为质量评审前置项**。Gold192、R50、Locked regression 等冻结评测集继续保持独立，避免数据泄漏到测试。

世界组件与历史 System 未完整核证的样本，**只能进入技术准备/质量候选，不能直接宣称训练准入**。在 CPU 上完成真实世界切分、Prompt 重建策略、Target 归属、去重、Tokenizer 和 Collator 验证后生成 SAFE 候选计数；训练数据冻结和 SFT GPU 另行授权。

## 5. 阶段闸门及单一事实来源

| 优先级 | 任务 | 完成的真实证据 |
|---|---|---|
| P0 | 冻结1000条只读核验 + 技术画像 | 官方 expand inspect PASS；全1000结构验证 PASS；质量状态仍独立 |
| P1 | 100条分层校准与独立误拒/漏拒评价 | 抽样覆盖、独立参考、Rubric对齐的 SAFE 汇总 |
| P2 | 首批50–100高质量训练候选 | 逐条质量判定与可追溯来源、未覆盖旧数据 |
| P3 | 训练格式/切分/Tokenizer/Collator | CPU 验收报告 |
| P4 | 单独批准训练数据准入/下一次 SFT | Owner 授权及训练预算 |

**明确暂停**：GLM 同25的再次H200、剩余8引文修复、Qwen第7条追加H200、三模型30条配对测试的扩大、1000条双模型GPU强制全覆盖、重复源池导出、重复 Tokenizer/Model Runtime Smoke。只有被证明是 P0–P3 数据交付的真实阻塞，才升级到对应工程任务，并单独批准费用。

## 6. 保留的限制与尚未完成事项

- 1000条采集成功 ≠ 本轮1000条技术画像已重跑 ≠ 质量PASS ≠ 训练准入。
- 旧记录包含 `quality_v1_admitted=0`，不能把首批 TRAIN_CANDIDATES 当作已批准训练。
- 不把3条前文称作完整故事上下文；不虚构当时真实 System。
- 不修改 RolePlay，不合并 PR #30，不上传私有正文/ID/哈希/交叉映射至 GitHub。
- 本次代码创建和 CI PASS 只证明合成代码，无 Owner 私有1000条现场 SAFE 时技术画像仍 HOLD。
