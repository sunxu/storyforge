# R60 P2-B / P3 工程实施记录（2026-11-10）

## 状态与门禁

P0 PASS、P1 PASS、P2-A COMPLETE（20/60，58/1/1，保留两项真实语义 HOLD）。本文件只记录新 P2-B/P3 工程，不修改历史裁决。

- P2-B：独立 30 case / 90 semantic checks Builder 与 Verifier 已提交；是否通过由对应 HEAD 的 Actions + Owner Mac SAFE 实际回执判断。**未经 Owner 审核不得标记 30/90 complete。**
- P3：三模型候选 Revision 已记录，静态 profile 与离线 tokenizer/template 工具已提交。真实 tokenizer CPU preflight、90 个私有输入预算、runtime/model config 及最终采样参数尚待实际验证。
- 不推理，不提交付费 HF Job，不启动 GPU、1000 条批量审核或 SFT。Quality-v1 admitted=0。

## P2-B 包生成（仅 Owner Mac，create-only）

工作树使用 PR #25 实际分支，先检查 git status、HEAD 与对应五项 Actions。Owner 私有路径不可在 GitHub 存放。

```bash
set -euo pipefail
cd /Users/keedle/workspace/storyforge-r60-ledger-diagnostics
git status --short --branch
git rev-parse HEAD

export PYTHONPATH=src:.
FREEZE="$HOME/.local/share/storyforge/r60/private/calibration-freeze-20261109"
OUT="$HOME/.local/share/storyforge/r60/private/p2b-heldout-owner30-v1"
test ! -e "$OUT"

python scripts/r60_owner_heldout_p2b_v1.py \
  --p0-freeze-dir "$FREEZE" --output-dir "$OUT"
```

期望 dry-run 状态为 `P2B_PREFLIGHT_PASS__NO_FILES_WRITTEN`，且 `cases_prepared=30`、`semantic_checks_expected=90`、`files_written=0`；必须人工核对无异常后才向**同一命令**追加 `--write`。成功写入六个 0600 文件于 0700 新目录，Builder 返回 `P2B_BLIND_PACKETS_READY__OWNER_REVIEW_NOT_STARTED`。若遇 PIN、split、去重等校验失败，返回 SAFE HOLD，不放宽门禁。

Owner 只审阅 P2B 盲包、说明与公开 Rubric v2.1；不可查看 ID Map、历史 A/B/C 裁决或 P2-A Development 对照来替代独立裁决。独立产生：

- `P2B_OWNER_RESULTS_PRIVATE.jsonl`，30 行，三维裁决。
- `P2B_SEMANTIC_CHECKS_PRIVATE.jsonl`，90 行，外层 `calibration_id, dimension, reviewed_at_utc, check`；check 与 P2-A 7 字段契约相同。

完成后运行：

```bash
python scripts/r60_owner_heldout_p2b_v1.py \
  --p0-freeze-dir "$FREEZE" --output-dir "$OUT" --verify
```

只有实际返回 `P2B_OWNER_REVIEW_COMPLETE__SEMANTIC_HOLDS_PRESERVED` 与 30/90 计数，才能报告 Owner 回执技术验收完成。真实语义 HOLD 原样保留。原始私有结果、映射、逐项裁决不可上传 GitHub；可单独抄录 SAFE 聚合。

## P3 Revision 候选与 CPU preflight

候选配置：`experiments/r60_quality/p3_model_profiles_candidate_v1.json`。

| 角色 | 模型 | Revision |
|---|---|---|
| A | Qwen/Qwen3-32B | `9216db5781bf21249d130ec9da846c4624c16137` |
| B | zai-org/GLM-4-32B-0414 | `077b5c2f5c43bd3239fd605a0600229e8facbd4a` |
| Challenger | zai-org/GLM-Z1-32B-0414 | `8eb2858992c1f749e2a6d4075455decc2484722d` |

Qwen3 Thinking 候选显式打开，使用官方建议的非 greedy 参数；GLM-4/GLM-Z1 的独立 generation config 参数未确认，不得填充 Qwen 参数或擅自进行推理。三模型来自既定计划，未替换模型。

离线检查要求在**已准备好的本地 tokenizer 快照**中按角色放置文件，路径布局 `$SNAPSHOTS_ROOT/{A,B,challenger}/<revision>/`。快照准备或任何收费资源另行确认，预检脚本本身不下载、不调用模型：

```bash
PYTHONPATH=src:. python scripts/r60_p3_cpu_model_preflight_v1.py \
  --snapshots-root "$SNAPSHOTS_ROOT" --input-budget 16384
```

16384 仅是命令示例预算，不代表 P3 已预注册或批准。预检检查 Python 包版本 `transformers==4.57.1`、`sentencepiece==0.2.1`、`jinja2==3.1.6`，调用各模型本地 tokenizer 的 `apply_chat_template`，输出 tokenizer 生成的合成输入 token 数与模板 SHA。其结果最高只能为 `P3_SYNTHETIC_CPU_PREFLIGHT_PASS__PRIVATE_90_PENDING`。完整 P3 PASS 仍需真实输入 90 项预算、模型 template/generation config、固定 prompt/rubric/profile/runtime 哈希与成本记录。

## 不得混淆的状态

- GitHub CI 合成 PASS ≠ Owner 30/90 回执 PASS；
- 30/90 Owner 回执 PASS ≠ held-out 对模型解盲；
- P3 合成 tokenizer PASS ≠ 90 个真实输入预检 PASS；
- P2/P3 工程 PASS ≠ P4 GPU、P6 1000 条审核或 SFT 授权；
- P2-A 的 58/1/1 两项 HOLD 不因后续工程被清除。
