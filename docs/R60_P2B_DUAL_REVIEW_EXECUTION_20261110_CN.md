# R60 P2-B 30/90 双模型盲审执行记录（SAFE）

状态：`P2B_AI_DUAL_REVIEW_COMPLETE__OWNER_CONFIRMATION_PENDING`。

可公开的聚合回执：`docs/evidence/R60_P2B_REVIEW_AGGREGATE_SAFE_20261110.json`。逐案内容只在 Owner 指定私有目录。

本轮使用冻结的 30 条 P2-B 盲包。Codex 与 Claude Opus 5.5 各完成 30 条案例、90 项三维 AI Advisory。两套结果均通过案例唯一覆盖、三态枚举、Rubric v2.1 结构合同和精确引用定位检查。AI Advisory 不代表 Owner 裁决。

## 聚合结果

| 维度 | 同判 | 分歧 | Codex 三态（支持/不支持/上下文不足） | Claude 三态（支持/不支持/上下文不足） |
| --- | ---: | ---: | ---: | ---: |
| player_agency | 27/30 | 3/30 | 3/27/0 | 2/28/0 |
| hard_rule | 10/30 | 20/30 | 0/10/20 | 0/30/0 |
| safety | 24/30 | 6/30 | 1/22/7 | 1/28/1 |
| 合计 | 61/90 | 29/90 | 4/59/27 | 3/86/1 |

两模型有 27/90 项提出额外故事上下文需求。精确引用定位无效为 0/90，但引用位置有效不证明引用在语义上支持裁决。全部 90/90 项的语义蕴含与三个维度仍须 Owner 逐项确认。私有 Owner 材料已覆盖 30/30 案例和 90/90 项，包含两模型证据、规则依据、理由及分歧。正式 Owner 三文件尚未生成，官方 30/90 Verifier 尚未运行。

## Claude 执行与恢复

- 使用 `https://4router.net/v1/chat/completions`、`claude-opus-5-5`、顶层 `system`、非流式、`max_tokens=12000`、300 秒超时；未发送 `temperature`。
- 观察到 7 次请求。其中首次请求在 12,000 token 上限截断，未生成有效批次，且旧客户端未保存该次用量；另外 6 次均有私有用量回执并完成 6 × 5 条。
- 可核查的 6 次请求用量为输入 95,445 tokens、输出 46,758 tokens。首次截断请求的用量与供应商实际计费金额未取得可靠账单，因此不估算总费用。
- 客户端保留每批原始响应与私有用量回执。适配器只做确定性合同规范化：85 个过短 coverage summary 补足，7 个引用角色映射，1 个由当前盲包唯一原文确认的消息定位修正，2 个规则枚举映射。模型 verdict、原文 quote、理由和 missing_context 均未改变。
- 没有读入 Codex 结果、Owner 标签或 ID Map 作为 Claude 请求内容。

## Owner 门禁与目录

本轮私有结果仅在 `~/.local/share/storyforge/r60/private/p2b-owner-review-20261110-v1/`，原始 P2-B 六文件仍在 `p2b-heldout-owner30-v1/`。私有目录模式为 0700，文件为 0600，新文件均 create-only；原始盲包与历史输出未被本轮覆盖。

Owner 应逐案核对三维 verdict、证据的语义支持性、规则适用性和全部上下文缺口。两模型同判的项目也需确认。只有 Owner 独立签署正式结果及语义复核后，才允许在独立目录运行分目录 Verifier，并写入 `P2B_REVIEW_FINAL_SAFE.json`。

本轮未运行 GPU、HF Job、SFT，未修改生产数据库。PR #25 保持 Draft。

## 工程验证

- 全套 pytest：936 passed、7 skipped、42 subtests passed（`TMPDIR=/private/tmp`，避开 macOS `/var` 符号链接与工作树未跟踪 `py.py` 对测试启动的影响）。
- 本次改动的 Python 文件 Ruff：PASS。
- `ruff check .`：FAIL，仓库历史文件累计 650 项现存诊断；本轮未批量改写这些无关文件。
