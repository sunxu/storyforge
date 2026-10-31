# StoryForge R58 G1 — 五个已知参数更新 Job 当前原始输入归档（SAFE）

日期：2026-10-31。状态：`FIVE_KNOWN_UPDATE_JOB_CURRENT_INPUT_OBJECTS_MATCH_PINS__HISTORICAL_EXPOSURE_G1_HOLD`。

**归档来源：Owner Mac 只读 HF Bucket 字节核验的 SAFE stdout + GitHub 冻结输入哈希。** 本次归档未亲自下载远端训练文件，也未重新执行 HF 核验。Owner 尚未在本轮提交完整测试套件重新通过的终端摘要，不能把先前失败的 334 测试擅自记为最新 PASS。

## 已知五次参数更新任务的当前输入核验

| 阶段 | 参数更新 Job 数 | 原始数据 Train / Validation | 本次匹配的现存 HF Bucket 对象 | Job 关联的记录位置 |
| --- | ---: | --- | ---: | ---: |
| v0.1 Smoke / Capacity / Baseline | 3 | 65 / 15 | **8**：共享来源 2、各任务编译输入 6 | **240**（每 Job 80） |
| R46 | 1 | 49 / 15 | 2：原始运行目录的编译输入 | 64 |
| R54 | 1 | 31 / 9 | 2：原始运行对应 Stage 的正式 release 输入 | 40 |
| **合计** | **5** | 三套已知数据 | **12**（其中 2 份共享源、10 份关联输入） | **344** |

- `344` 是五个 Job 关联的 split 记录位置之和，**不代表 344 条不同样本**，更不证明每条发生过反向传播；单步 Smoke / Capacity 尤其不能据此认为 65 个训练样本全数获得梯度。
- 三套冻结数据只有 **184 个不同 Job 不加权的 Train / Validation 位置**（65+15、49+15、31+9）；不同数据集和世界可能重叠。
- v0.1 的 Train / Validation 编译结果是使用 Git 中固定的历史 `prepare_sft.py` 字节重放后，对每个任务现存编译文件逐一 SHA256 对照。
- R46 对照的是其原始运行目录的 `train.jsonl` / `validation.jsonl`；R54 对照的是同一次运行的上传 Stage release 文件。它们属于不同结构，不可假装 R54 在每个 Job 目录生成了单独训练文件。
- SHA256 已归档，R50 内容、私有 UUID、HF 凭据、原始运行命令及训练正文均不包含在新增提交中。

## 可追溯来源

机器可读联合回执：`docs/evidence/R58_G1_KNOWN_FIVE_JOB_CURRENT_PRIMARY_INPUTS_CROSSCHECK_SAFE_20261031.json`。

Owner 本轮 v0.1 返回：
`docs/evidence/R58_G1_V01_HF_PRIMARY_INPUT_OWNER_MAC_SAFE_RECEIPT_20261031.json`。
此前 R46/R54 返回：
`docs/evidence/R58_G1_R46_R54_HF_PRIMARY_INPUT_OWNER_MAC_SAFE_RECEIPT_20261031.json`。
冻结索引：
`docs/evidence/R58_G1_GITHUB_HISTORICAL_TRAINING_SOURCES_SAFE_20261031.json`。

v0.1 编译哈希（SAFE）：
- Train SHA256：`68a535fcb0fd9249c630d31e2623a9708f700b9ece27388f4a34fd5166ab84af`
- Validation SHA256：`138f3cbff7914337db2e2d438f335573c5c4d770f0e390186e4bc9f70b085557`

## 剩余 G1 硬缺口

1. **历史运行时一致性：** 现存 Bucket 文件内容与 Git 哈希相同，不能仅靠此证明当年 Job 在读取时绝无文件变化；尚未证明历史对象版本不可变或有完整可信的每 Job 运行时原始输入证据。
2. **未分类任务：** 上次只读盘点中的其余 60 个 Job 尚未充分分类；其他命名空间、被删任务和日志保留完整性也没有保证。不能宣称全部历史实际训练来源完整。
3. **额外受保护世界：** R50 及其他受保护数据覆盖的完整性尚未证明；本轮没有打开 R50 测试正文。
4. **准入：** G1 继续 `HOLD`；Train / Validation / Teacher = `0/0/0`、`expansion_allowed=false`。PR #7 继续 Draft；不授权新 HF Job、训练或扩样。

**后续工作方向：** 优先将这一份统一来源证据与 R58 候选的私有冻结世界索引进行已有元数据层级的最终对账；若坚持“所有历史训练 Job 完整”的强标准，未分类任务仍需要另外处理，不应仅凭这五个已知 Job 的核验解除 G1。
