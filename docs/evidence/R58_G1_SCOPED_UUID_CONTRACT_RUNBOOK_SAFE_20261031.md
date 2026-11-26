# R58 Skill v0.2 — G1 八范围 UUID 元数据契约与核对（SAFE）

日期：2026-10-31。**状态：契约实现与合成测试完成；Owner 真实八范围聚合尚未执行；G1/G2 仍 HOLD。**

## 定位

此工具不替换 R50 密封保护集、不扫描生产库、不下载 HF 或私有对话。它只供 Owner 在已授权、已准备好的**世界 UUID 元数据**上做交集复核。保持既定 Round1 五世界，历史 SFT 精确曝光一个继续排除，剩余四个继续 HOLD。任何「零交集」只限指定来源快照，不能证明世界从未训练或未受保护。

新增：

- `skills/storyforge-roleplay-sft/v02/r58_g1_scope_reconcile.py`：私有只读八范围 UUID 交集检查，输出 SAFE 聚合；
- `skills/storyforge-roleplay-sft/v02/test_r58_g1_scope_reconcile.py`：只用虚构 UUID 的合成测试；
- `r58_pipeline_bridge.py g1-audit`：Skill v0.2 入口，不允许修改 `shortlist/gate/freeze` 的准入逻辑。

## 八个来源范围

| scope | 历史已知来源范围 | 本次局部期望行数 | 独立全集证明 |
|---|---|---:|---|
| `known_historical_sft` | 旧 R57 冻结已训练故事精确 UUID | 27 | 无 |
| `r50_known_protected` | 已授权的 R50 五世界**元数据** | 5 | 仅五世界局部 |
| `gold195_source` | Gold87+Gold108 的来源世界 | 13 | 非全部 DEV |
| `legacy_dev20` | 旧 v0.1 Test/DEV20 两世界**元数据** | 2 | 非全部 DEV |
| `r04_non_gold` | 旧 R04 非 Gold 两世界 | 2 | 非全部保留世界 |
| `r55_r57_other_dev` | 其他开发/仲裁已曝光世界 | 待查 | 缺失 |
| `other_reserved_heldout` | 其余冻结、保留、Held-out 世界 | 待查 | 缺失 |
| `other_historical_training` | 五已知 Job 以外实际参数更新任务的世界 | 待查 | 缺失 |

不可为了让 `OWNER_COMPLETE` 出现就臆造缺失索引；未找到权威元数据时以空列表和 `UNKNOWN` 占位，仍为 HOLD。尤其 **R50 只允许已获批准的保护集合 UUID 元数据，不得读取保护题目、目标回答、评分或测试正文**。

## 本地输入契约（不得提交至 GitHub）

Owner 需在已有 `~/.storyforge-r58-private/` 的 0700 目录中，准备只含下列字段的 0600 JSON：

- 顶层严格四字段：`schema=r58_g1_private_scoped_uuid_manifest_v1`、`world_identity_policy=ONE_ROLEPLAY_STORY_UUID_PER_WORLD`、`candidate_uuids`（冻结的五个规范小写 story UUID）、`source_scopes`（上述八范围各一次）；
- 每个 scope 严格五字段：`scope`、`world_uuids`（只含规范小写 UUID；未知范围可空列表）、`roster_sha256`、`coverage_claim`、`source_revision`；
- `roster_sha256` 仅是本地名册规范排序后的 SHA256：每个小写 UUID 后附 `\\n`（LF），空集合对应空字节的 SHA256。它能发现本地列表漂移，**不能证明来源快照真实或全集完整**；
- `coverage_claim` 只允许 `UNKNOWN`、`OWNER_PARTIAL`、`OWNER_COMPLETE`；即使是 `OWNER_COMPLETE` 也不会放行。使用 `OWNER_COMPLETE` 时必须记录 40 或 64 位小写十六进制 `source_revision`，但仅有这个字段仍非独立历史证明；
- 禁止在这个 JSON 放入任何 Prompt、故事正文、测试样本、request ID、会话 ID、用户 ID 或私有真实路径。

第二个输入必须是**已存在的五故事** `g1_prior_sft_uuid_owner_policy_v2_private.json`，不是重新生成的替代队列。校验器会验证原有账本 schema、五故事精确一致、一个已曝光排除、四个仍 HOLD、所有训练准入和保护 flags 均为 false。输入文件缺失、权限过宽、符号链接、UUID 非规范、SHA 不符或来源集合冲突，一律退出码 42，stderr 不泄漏私人路径。

## 执行命令

先只运行无需私有材料的合成测试：

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
python3 -m unittest discover -s skills/storyforge-roleplay-sft/v02 -p 'test_*.py' -q
ruff check skills/storyforge-roleplay-sft/v02/ --statistics
```

如果本地已有**经授权整理完成**的八范围 UUID-only manifest，再执行（以下文件名只是预留，不要求为了测试新访问 R50）：

```bash
ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
python3 skills/storyforge-roleplay-sft/v02/r58_pipeline_bridge.py g1-audit \
  --private-manifest "$ROOT/g1_scoped_uuid_manifest_PRIVATE.json" \
  --prior-sft-ledger "$ROOT/g1_prior_sft_uuid_owner_policy_v2_private.json"
```

只回传 stdout 的 **SAFE 计数与状态**；**绝不上传或在聊天中粘贴**私有 manifest、含 UUID 的源清单或原有账本。如果 manifest 还没准备好，本轮到此为止，记录 `NOT_EXECUTED__MISSING_AUTHORIZED_INDEX`，不自行扫描或补选候选。

## 结果语义与下一阶段

正常完成的是 `SCOPED_UUID_RECONCILED__ALL_UNVERIFIED_COVERAGE_HOLD`；stdout 只含每个 scope 的行数、剩余四世界的交集数、来源版本是否填写、来源声明等级。**退出 0 表示“局部元数据契约可解析、交集已计算”，而不是 G1 PASS**。即使八范围都声明 `OWNER_COMPLETE`，结果仍是 `g1_clearance=HOLD`、独立完整范围数量 0、Train/Validation/Teacher 为 0。

真正解除 G1 仍需分开证明历史实际参数更新 Job 的全集、所有训练输入和保护世界权威集合来源。G2 仍需可信历史 target↔request 绑定与 Provider 原始字节；不得凭时间接近、当前数据或 SOURCE_PIN 代替原始运行证明。

本轮不扩大 5 世界／20 回复，不触碰 R50 正文，不启动任何付费 HF CPU/GPU Job，不修改 v0.1 冻结文件，不将 PR #7 从 Draft 改为 Ready。
