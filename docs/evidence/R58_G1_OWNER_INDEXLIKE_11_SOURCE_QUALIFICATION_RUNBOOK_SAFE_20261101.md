# R58 G1 — Owner 本地 11 条索引类名称线索的来源资格核对（SAFE）

2026-11-01，Draft PR #7，仅适用于 `r58/roleplay-sft-skill-v01`。

## 当前基线

Owner Mac 已完成 7/7 合成测试，成功复用旧 PRIVATE 22 个不同文件路径、29 条范围关联，并独占创建新的 0600 PRIVATE 审阅表。原始五范围来源证据清单未修改；29 条关联的 `owner_approved_metadata_only_source=false`。本轮来源及计数 SAFE 回执见 `docs/evidence/R58_G1_EXISTING_22_FILENAME_CANDIDATES_OWNER_RECEIPT_SAFE_20261101.json`。

四组文件名提示数量：`INDEX_HINT_ONLY=8`、`INDEX_AND_REPORT=3`、`REPORT_HINT_ONLY=12`、`OTHER_NAME_HINT=6`。**这 11 条索引类范围关联不一定是 11 个不同文件；它们只是优先审阅顺序，尚无一项证明是合格元数据索引。**

## 唯一下一步：Owner 本地只看候选路径名称，不自动读内容

在正确 R58 分支和已配置上游的 Owner Mac 工作区执行：

```bash
git pull --ff-only
ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
REVIEW="$ROOT/g1_existing_candidates_owner_review_PRIVATE_20261101.json"
test -f "$REVIEW" && test ! -L "$REVIEW" || { echo 'SAFE_HOLD: PRIVATE_REVIEW_NOT_AVAILABLE'; exit 42; }
jq -r '.entries_PRIVATE | to_entries[]
  | select(.value.index_like_filename_hint)
  | [(.key + 1), .value.scope, .value.source_reference_PRIVATE,
     .value.index_like_filename_hint, .value.report_like_filename_hint]
  | @tsv' "$REVIEW" | less -S
```

**命令会在 Owner 本机屏幕展示 PRIVATE 完整路径。不要复制终端显示结果到聊天或 GitHub，也不要通过远程 CI 执行这项带私有路径的列示。** 命令只读已经生成的 PRIVATE Review JSON，没有读取任何候选源文件；不写回或批准原有清单。

针对 11 条提示，Owner 只根据已有的可信来源登记、冻结指南、仓库公开 SAFE 回执判断：

1. 是否能够证明它是**专用 UUID/世界元数据索引**，而不是 R55 仲裁正文、模型输出、故事/Prompt、R50 密封材料或仅 count-only 报告？无法确认就保持未审。**不要为了确认而直接打开不明内容的文件。**
2. 是否有来源版本 pin、冻结时间、实际覆盖范围（包括未被命名为 R55/R57 的其他 DEV/heldout）、Owner 数据来源责任边界？缺一项不填 `OWNER_COVERAGE_ATTESTED`。
3. 是否已获准使用这个来源范围的 metadata-only world/story UUID？R50 必须通过独立授权的保护世界元数据登记，不允许因 R50 文件名发现为 0 而主动扫 R50。

## 向本对话反馈的最小 SAFE 摘要

只回复**各 scope 是否找到了可审阅的 metadata-only 来源**和仍未确认的 scope 数量；可以只用中文描述范围名称与数量。不要返回路径、文件名、内部 SHA、故事 UUID、Reviewer 结论或文件内容。

本轮不是来源全集审核，也不是自动填清单。未发现合规的元数据专用索引时，应明确 `AUTHENTICATED_METADATA_INDEX_NOT_LOCATED__HOLD`，而非伪造或创建新世界索引。若找到可审阅候选，下阶段单独审查其来源版本和覆盖证明，再决定是否允许读取 UUID-only 元数据，绝不直接设置 G1=PASS。

**停止条件：** 未经证明的索引、未知冻结版本、无覆盖权威声明或任何 R50/原始内容风险，都保持 `G1=HOLD`、`G2=HOLD`、`G3=NOT_STARTED`、`Train/Validation/Teacher=0`、`expansion_allowed=false`。不启动 HF Job、不训练、不扩样、不修改 Skill/main。
