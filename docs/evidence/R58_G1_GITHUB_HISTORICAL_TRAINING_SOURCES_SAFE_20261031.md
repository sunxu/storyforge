# StoryForge R58 G1 — GitHub 优先的历史训练材料统一索引（SAFE）

日期：2026-10-31。**范围：当前已知的历史训练来源**，不是 Hugging Face 全部历史任务的完整性证明；此提交不包含新增样本、故事正文、R50 保护内容、R58 候选 UUID、私有训练 JSONL、用户私有账本或密钥。

## 为什么调整路线

R58 G1 的目标是避免新训练候选与既有模型训练/验证及其他受保护数据发生不合规重叠，而不是将全部 HF Jobs 逐个归类。此前 Owner Mac 已对账六份已知 Train/Validation 冻结来源：**145 Train + 39 Validation = 184 split placements，来源世界 27 个**；这不是 184 个互异样本，也不是 184 次真实反向传播。R57 私有来源名录和 R56 私有逐 UUID 索引的核验结果只能作为 **Owner 本机回执级** 证据，不能在公开 Git 文档中重放成逐 UUID 明文。

本轮将可验证的公开数据身份、实际运行的登记证据和待核查事项**分层提交 GitHub**。后续可优先重用本清单，再有针对性地读取已有的 HF 原始训练输入，而不是默认追查全部未分类 Job。

## 冻结来源（六个 split）

| 阶段 | Train | Validation | 证据等级 | 公开源码 / 证明来源 |
| --- | ---: | ---: | --- | --- |
| v0.1 | 65 | 15 | **GIT_CONTENT_AND_SHA256**，实际 Train/Validation JSONL 原始字节在 Git | `data/compiled/v0.3/{train,validation}.jsonl`、`SHA256SUMS.txt` |
| R46 | 49 | 15 | **GIT_RECEIPT_PLUS_OWNER_REMOTE_INPUT_ATTESTATION**，编译后 SHA 在报告中；部分真实远端文件仍仅有 Owner 验证回执 | `docs/evidence/V02_R46_GPU_TRAINING_ACCEPTANCE_20261014.json`、`V03_R53_R46_PRIMARY_EXPORT_OWNER_RECEIPT_VERIFIED_20261021.md` |
| R54 | 31 | 9 | **GIT_PINNED_PRIVATE_RELEASE_AND_RUNNER_CONTRACT**，训练输入属于此前正式私有发布；Git 保留其 SHA 和 GPU runner 执行约束 | `V03_R53_FORMAL_PRIVATE_31_9_RELEASE_OWNER_RECEIPT_ACCEPTED_20261021.md`、`scripts/v03_r54_gpu_runner.py` |
| **合计** | **145** | **39** | **184 次记录位置，未去重** | 仅含已登记的三次 SFT 正式/探索训练 |

这些来源的可公开 SHA256、不可变 Git blob ID、数据规模、相关 Job ID（仓库已有公开 ID）和证明等级见机器可读清单：

`docs/evidence/R58_G1_GITHUB_HISTORICAL_TRAINING_SOURCES_SAFE_20261031.json`

> **重要区别：** 这里的 v0.1 内容证明是在 GitHub 的真实 JSONL 上复算；R46、R54 的脚本只对比**Git 中冻结证据记载的编译哈希和声明**，不能重新哈希缺席的私有 HF 实际训练输入，不能把 Owner 回执擅自提升成独立 HF Provider 证明。

## 早期参数更新和受保护开发来源

已登记的**五次实际参数更新 Job**：v0.1 Rank32 Smoke（3 步）、Rank64 Capacity（1 步）、Baseline（9 步）、R46（7 步）、R54（16 步）。Smoke / Capacity 虽非正式训练版本，仍须算作历史训练曝光；GitHub 有 v0.1 数据路径、Smoke 配置和运行报告，但**尚未逐任务独立重哈希远端原始输入**。不能仅凭它们复用相同配置就声称逐样本训练执行已证明。

v0.1 `test.jsonl` **20 条**属于旧 Held-out / 开发使用记录，不是这六份 Trainer Train/Validation split；R04 150、Gold195 等是已另行核验的策展/开发/保护来源，**不能自动把它们全部列作 Trainer 参数更新数据**。R56 故事 07 / 11 的冻结编号到 UUID 映射，以及与 R58 剩余 4 个候选的零精确 UUID 交集，已有先前 Owner Mac SAFE 回执；本提交不导出 UUID 或受保护原文。

## 只读本机验证（无 HF / 不读私有账本）

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
python3 -m unittest discover -s experiments/r58_round1 -p 'test_*.py' -q
python3 experiments/r58_round1/verify_github_historical_training_sources.py --repo-root "$PWD"
```

验证器只通过 `git cat-file blob <固定SHA>` 取 11 个历史 Git 对象：对于 v0.1 两份 JSONL，仅验证完整文件 SHA256、行数与结构性 `metadata.story_id` / 样本 `id`，**绝不 JSON 反序列化对话正文**；对于 R46 使用冻结 JSON 报告及 Owner 回执文本；R54 使用冻结正式发布回执和 runner 的 `EXPECTED` **AST 字面量**（不运行 runner），另查 Smoke/Capacity/Baseline 的既有证据。只向 stdout 打印 SAFE 计数/布尔值，不记录 UUID 或原始文本，也不触及 R50 / HF / GPU / 私有账本。若 PIN、数量、证明等级不一致，返回 `HOLD` / exit 42。单元测试使用人工合成内容，不读取真实故事。

## 无法由 GitHub 独立解决的缺口

- R46 与 R54 的 **HF Trainer 实际输入文件**仍应按已有 Owner 验证回执的可信层级表述；没有原始文件字节的重新独立核验，不应宣称与运行时数据完全一致。
- Smoke 和 Capacity 的确切远端输入及读入行为，不能仅由共享 Git 配置证明。
- 之前 `adradar` 可见 HF Job 共 69 个：5 个已知参数更新、4 个有用途文档、60 个尚未充分分类；其中 1 个 `CANCELED` GPU Job 有训练遥测迹象，但未确认参数更新。**这些未分类任务不能仅凭 Git 目录列举排除**；其他命名空间、删除或超过留存窗口的 Job 也未证明不存在。
- `27` 世界是前轮 Owner 私有冻结索引交叉验证结论，**不是本轮公开 JSONL 独立重算的全部 27 UUID**；可能存在非精确 UUID 的同世界/关联角色曝光。
- 本轮不读取 R50；不改变之前受保护测试和 R58 五故事队列的隔离状态。

因此，**`source_registry_complete=false`、`all_actual_sft_runs_and_input_sources_proven_complete=false`、G1=`HOLD`**。Train / Validation / Teacher 新准入继续为 0，禁止扩样、训练和自动解除 G2/G3。PR #7 保持 Draft。后续核验优先直接比对已有 HF Bucket 输入字节及历史源码 SHA，与此 Git 索引对账；无需先追查 60 个未知 Job 的每条原始日志。
