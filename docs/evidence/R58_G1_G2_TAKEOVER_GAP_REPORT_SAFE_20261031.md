# StoryForge R58 — G1/G2 交接与证据覆盖缺口（SAFE）

日期：2026-10-31。对象：Draft PR #7 / `r58/roleplay-sft-skill-v01`。**G1=HOLD；G2=HOLD；Train/Validation/Teacher 准入 0/0/0。** 本报告只汇总 GitHub 已归档 SAFE 索引与 Owner 回执，不打开故事原文、R50 试题、HF 原始历史请求或私有 UUID。

## G1：观察到的范围不等于完整来源证明

| 范围 | SAFE 证据与局部交集核验 | 尚缺的证明 |
|---|---|---|
| 历史 SFT | v0.1/R46/R54 六份 Train/Validation split 共 **184 个记录位置**；Owner 私有索引报告 **27 个来源世界**。五个已知参数更新 Job 对应 **344 个记录位置**，当前 HF **12 个对象**匹配冻结哈希 | 184/344 均非去重案例数；无法证明实际 Job 当时读取的字节、每例梯度覆盖与历史 Job 全集 |
| 固定 Round1 | 五个候选世界中的 **1 个与历史 SFT UUID 精确重叠并排除**；剩余四个固定、不补选 | 四个仍 HOLD，不能直接读候选正文 |
| R50 Protected | Owner 对剩余四个与 R50 五个冻结世界的精确 UUID 检查为 0，未打开 R50 内容 | 仅限已核五世界；其他 Protected 全集证据缺失 |
| Gold195 | Owner 已报告对 13 个来源世界的精确 UUID 排除 | Gold195 不等于所有开发和评估来源 |
| DEV20 / R04 | Owner 已有范围回执分别报告与 DEV20 两世界、R04 非 Gold 两世界精确 UUID 未命中 | 需核实索引版本、完整性，以及其他 DEV/Protected 的覆盖 |
| 其他保留来源 | R55/R56/R57 等尚无完整权威世界索引 | 缺少全集覆盖证据，不可将“未发现”当作“没有” |
| 其他 HF Job | 曾见 69 个历史 Job，其中 60 个未充分分类；部分取消 GPU 任务有训练遥测 | 不可假设 60 个全部训练或全部没训练；要只读核对实际参数更新与输入来源 |

Owner 已确定 R58 的世界键为 **同一 RolePlay story UUID = 一个独立世界**，无需重新做跨 UUID 别名图。但这只定义世界身份键，**不替代**历史曝光和保护全集核验。上述 Owner 提供的局部精确交集均不等于 G1 最终 PASS。

SAFE 来源：

- `R58_G1_G2_SKILL_V02_READINESS_MATRIX_SAFE_20261031.json`
- `R58_G1_GITHUB_HISTORICAL_TRAINING_SOURCES_SAFE_20261031.json`
- `R58_G1_KNOWN_FIVE_JOB_CURRENT_PRIMARY_INPUTS_CROSSCHECK_SAFE_20261031.json`
- `R58_ROUND1_METADATA_PILOT_GATE_SAFE_20261030.json`
- `R58_ROUND1_G1_EVIDENCE_COVERAGE_SAFE_20261030.json`

## G2：不把条件性历史重建冒充原始请求

Pinned RolePlay 源码识别出 **19 个 Prompt 组装组件，17 项字节级阻塞**。三个固定历史目标仅有条件性 11 条消息历史与 33 条消息的当前修订 Ledger 对账；历史 target↔request_id 的直接因果关联、Provider 原始输入字节、目标时点部署 SHA 仍未认证。软时间候选 **2/4/2** 不唯一，必须遵守停止规则，不再靠“最接近时间”推断 PASS。

详见 `R58_PRIORITY3_PROMPT_ASSEMBLY_GAP_MATRIX_SAFE_20261030.json` 与 `R58_PRIORITY3_REQUEST_LINK_STOP_RULE_AND_NEXT_GATES_SAFE_20261030.md`。

## 可复现安全核验

在 R58 分支完整 Git 检出运行：

```bash
python3 -m unittest discover -s skills/storyforge-roleplay-sft/v02 -p 'test_*.py' -q
python3 skills/storyforge-roleplay-sft/v02/r58_evidence_preflight.py --repo-root "$PWD"
python3 skills/storyforge-roleplay-sft/v02/r58_pipeline_bridge.py gate --repo-root "$PWD"
# gate 正常拒绝时退出 42，返回 SAFE HOLD；不能把退出 42 算作准入 PASS
```

`r58_evidence_preflight.py` 只核对固定 Git blob 和门禁一致性，**不能独立认证缺失的历史全集**。v0.2 桥接 `gate/freeze` 当前只会拒绝，不调用 v0.1，不创建冻结数据；`shortlist` 只输出 SAFE 元数据统计，不重新选取五个固定候选。

解除阻塞必须提供：G1 历史实际更新 Job/输入全集和所有 Protected/DEV/保留 UUID 的权威冻结元数据；G2 可信历史 target↔request 绑定、原始 Provider 请求或足以证明字节级相等的当时完整 Runtime 记录。缺证据继续 HOLD。之后才允许在原定最多五世界/20 回复内开展 G3 双 Reviewer 与 Owner 审核。未获明确授权不得扩样、访问 R50 试题、运行付费 HF CPU/GPU、冻结 v0.4、合并 PR 或晋升模型。

**本报告是缺口矩阵的中文解释，不是阶段验收或训练授权。**
