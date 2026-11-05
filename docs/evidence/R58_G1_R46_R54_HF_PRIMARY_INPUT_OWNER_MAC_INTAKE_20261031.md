# R58 G1 — R46 / R54 原始远端输入 Owner Mac SHA256 回执（SAFE）

日期：2026-10-31。本回执来自 Owner 在对话中返回的 `check_hf_primary_input_bytes.py` SAFE stdout；**本轮 GitHub 提交本身没有读取 HF Bucket 或重新运行 SHA256**。

## 本机报告的成功核验

| 原始运行 | 只读核验对象 | Train | Validation | 结果 |
| --- | ---: | ---: | ---: | --- |
| R46 | 2 | 49 | 15 | 当前原始运行编译文件的 SHA256 与冻结 Git 回执一致 |
| R54 | 2 | 31 | 9 | 当前实际运行对应的上传 Stage release SHA256 与 Git 冻结合约一致 |
| **合计** | **4** | **80** | **24** | **104 个 split 记录位置** |

Owner 明确启用了只读私有 Bucket 字节核验；脚本仅逐块计算 SHA256 / 行数，不输出远端 URI、私有训练正文、故事 UUID、异常详情或凭据。没有提交新 HF Job，也没有读取 R50 故事正文。

可机器读取的原样字段与来源等级保存在 `R58_G1_R46_R54_HF_PRIMARY_INPUT_OWNER_MAC_SAFE_RECEIPT_20261031.json`。本档案只有 SAFE 汇总，不是原始训练产物、独立 HF 供应商证明，或训练时不可变证书。

## 严格证据边界

- 当前 Bucket 对象与原先 SHA256 相同，**不能单独证明历史 GPU 运行当时读取到的字节一定相同**；过去的 Bucket 文件变更历史、版本不可变性或有签名的运行时摘要尚未核实。
- R46/R54 四份文件未做语义或内容审阅，不证明源文本绝不含 R50。
- 此步骤没有分类其他 HF Job，不证明历史训练来源全集完整；不核准 R58 训练或扩样。
- 已知六份 Train / Validation 共 184 记录位置，v0.1 的 80 记录位置已由 Git 内容直接确认；R46/R54 的 104 记录位置由本轮**Owner Mac 当前 HF 字节**核验。不能因此宣称 184 个记录位置的每一条都实际更新了权重。

## 后续建议

1. 整理 v0.1 Smoke、Capacity、Baseline 的**实际输入来源**，分清 Git 冻结源字节、共享 HF 上传源文件和每个 Job 自身的运行时输入证据。优先使用 GitHub 已有的提交脚本、运行记录和固定哈希，不需要逐项重扫 60 个未知 Job。
2. 对 R46/R54，若未来需要更强的历史运行时证明，优先查已存在的 Worker 输入哈希 / Trainer report，不触碰训练正文。
3. 继续维持 `all_actual_sft_runs_and_input_sources_proven_complete=false`，`source_registry_complete=false`、`G1=HOLD`、Train / Validation / Teacher 准入 0、`expansion_allowed=false`。PR #7 继续 Draft。

参考：`docs/evidence/R58_G1_R46_R54_HF_PRIMARY_INPUT_BYTE_AUDIT_RUNBOOK_SAFE_20261031.md`。
