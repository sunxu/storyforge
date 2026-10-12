# StoryForge v0.2｜Reviewer A 8 条证据补正核验（组织者附录）

**核验状态：`CORRECTIONS_TRACED__ONE_FORMAT_EXCEPTION`**  
**训练准入：`PENDING_NOT_APPROVED`**

## 核验结果

| 检查 | 核验结果 |
|---|---:|
| 需补正的匿名 ID | 8/8 完整 |
| 与原版分发的 122 个样本正文一致 | 122/122（另 1 README 不变） |
| 原评分、结论、严重错误代码、上下文充分性 | 8/8 无改动 |
| 原理由实质错误并作出更正 | 2（SF2-001、SF2-073） |
| 仅更正引用方式 | 6 |
| 更正后证据的原文句段能够定位 | 26/26 |
| 整条引文为连续、完全相同文本 | **22/26** |
| 8 条记录严格连续引文全部通过 | **7/8** |
| 尚有逐字引文格式问题 | **SF2-073，4 处** |

### 各条处置

| 匿名 ID | Reviewer A 自述的修改类型 | 我方逐字核验 | 后续 |
|---|---|---|---|
| SF2-001 | 原理由实质修正 | 3/3 连续匹配 | 保留附录 |
| SF2-002 | 仅引用格式修正 | 3/3 连续匹配 | 保留附录 |
| SF2-014 | 仅引用格式修正 | 2/2 连续匹配 | 仍 HOLD |
| SF2-024 | 仅引用格式修正 | 4/4 连续匹配 | 保留附录 |
| SF2-041 | 仅引用格式修正 | 3/3 连续匹配 | 保留附录 |
| **SF2-073** | 原理由实质修正 | **0/4 整段连续；拆分后 4/4 均可定位** | **需 Reviewer A 确认逐字分段引用** |
| SF2-109 | 仅引用格式修正 | 3/3 连续匹配 | 保留附录 |
| SF2-114 | 仅引用格式修正 | 4/4 连续匹配 | 保留附录 |

**审核依据：** Reviewer A 最初分发的匿名样本、Reviewer A 已完成的 122 条原始评分、及本轮独立上传的补正 Markdown。逐字核查只检查目标助手回复，历史助手不计入修正后的目标证据。

本轮已确认 SF2-001 与 SF2-073 的**原理由误用了历史 Assistant 内容**；此次 Reviewer A 的新理由符合当前目标回复的主要内容。这是理由溯源核验，不是第三方重新给 Gold 打分。其余 6 条是引文形式更正。所有 8 条原结论保持不变。

## 对联合评审统计的影响

- 原来 **112 条原候选**中 **87 条局部双 ACCEPT、19 条待补证、6 条需仲裁**：因本次无评分/结论变化，**数量不变**。
- 10 条隐藏对照仍需要按原计划核查；其中 SF2-014 属于对照，原状态 HOLD，本次依然 HOLD。
- 本次只解决了 Review A 的引文与理由问题，**不替代 Review C 对争议样本的独立评分**；也不意味着角色卡、全局历史或训练工程门禁 PASS。

## 文件和审计边界

- `00_reviewer_A_original_correction.md`：用户上传的补正，逐字复制不修改。
- `02_audit_details.json`：逐条引文、出现位置、分数与结论对比，以及输入 SHA256。
- `03_append_only_A_evidence_patch_PRIVATE.csv`：可供组织者使用的追加式差异记录。不能用它覆盖原始 122 条评分表；其中 `verbatim_segments_verified_from_target` 列是**组织者自动拆分验证结果**，不应伪装成 Reviewer A 自己修订过的原句。
- `04_SF2-073_逐字证据建议.md`：待 Reviewer A 复核确认的建议文本。
- `verify_reviewer_a_corrections.py`：CPU/标准库离线复核脚本。
- `SHA256SUMS.txt`：本包文件哈希。

## 复现方法

保持最初的 A 评审 ZIP、已提交的 A 完成版 ZIP 与这次的补正 MD 不变：

```bash
python3 verify_reviewer_a_corrections.py \
  --correction '00_reviewer_A_original_correction.md' \
  --original-a 'StoryForge_v02_JointReview_Reviewer_A.zip' \
  --submitted-a 'StoryForge_v02_JointReview_Reviewer_A_completed(1).zip' \
  --report /tmp/reviewer_a_audit.json
```

本包不包含 Reviewer B 的评分、模型真实身份映射或任何未经核实的训练通过声明；本次未使用 HF Job/GPU，未写入 GitHub 或移动 v0.1 冻结标签。
