# R58 Gold192 候选范围决策与执行说明

日期：2026-11-02。Owner 已明确批准：在本轮 Gold195 质量优先 LoRA 流程中，**排除 3 条冻结 Gold108 缺少世界身份的记录**，不再以其世界身份恢复作为其余候选的前置任务。

## 决策与范围

- Gold195 原始冻结索引、Gold 目标和私人原始审核任务保持完整且不变。
- 本轮排除的 3 条仅以受控私人分流清单中的 `WORLD_OR_TARGET_IDENTITY_HOLD` 判定；标记 `EXCLUDED_WORLD_ID_UNRESOLVED`，不参与本轮 Train/Validation，也不能进入密封 Test。
- 本轮候选集上限为 **192 = Gold87 的 87 + Gold108 的 105**。这只是候选范围，不等于已正式批准 192 条样本训练。
- Gold87 的 87 条需补齐历史 A/B 证据绑定；Gold108 的 105 条需继续上下文/世界卡语义审核；旧五维 ACCEPT 不等于六维 PASS。
- 以后若恢复三条世界身份，应通过新的显式版本和 Owner 审批重新加入，不能改变本次范围或偷偷复用旧名单。
- 历史 R46/R54 训练与验证曝光必须作为后续世界级分割和评测去污染的约束。曾用于 Train 的 Gold 并不自动禁止重新训练，但已曝光案例不能声称是独立的未见评测。
- 用户尚未批准本轮 GPU/LoRA 训练，`quality_v1_admitted=0`。

## 执行方式

GitHub 新增 `experiments/r58_quality/gold192_scope_exclusion.py`，只验证私人 Gold195 任务与已完成的私人分流清单是否集合一致、任务目标与输入 SHA256 是否自洽、是否恰好 105/87/3。默认只输出 SAFE JSON；不读取 R50，不启动网络或 GPU，不生成训练文件，也不修改冻结数据。

Owner 在 Mac 的 StoryForge 仓库根目录执行：

```bash
git pull --ff-only
python3 -m unittest discover -s experiments/r58_quality -p 'test_gold192_scope_exclusion.py' -v
ruff check experiments/r58_quality/gold192_scope_exclusion.py experiments/r58_quality/test_gold192_scope_exclusion.py
python3 experiments/r58_quality/gold192_scope_exclusion.py \
  --repo-root "$PWD" \
  --private-tasks "$HOME/.local/share/storyforge/r58/gold195-review-tasks-v1.jsonl" \
  --private-queue "$HOME/.local/share/storyforge/r58/legacy-reuse-queue-v1.jsonl"
```

成功的 SAFE 状态为 `GOLD192_SCOPE_VALIDATED__QUALITY_HOLD`；此时只说明候选范围验证成功。失败时 `GOLD192_SCOPE_INVALID__HOLD`，不可宣称冻结完成。

## 下一步

先按这份冻结范围继续 Gold87 历史审核证据绑定、192 条上下文语义差异检查，再生成正式的训练资格名单与按世界隔离的 Train/Validation 分组；不以历史精确生产请求回放作为训练前置任务。

## 私人范围清单（非训练数据）

通过以上 SAFE 范围验证和 Ruff 后，再执行如下命令；目标文件必须不存在，工具拒绝覆盖：

~~~bash
python3 experiments/r58_quality/gold192_scope_manifest.py \
  --repo-root "$PWD" \
  --private-tasks "$HOME/.local/share/storyforge/r58/gold195-review-tasks-v1.jsonl" \
  --private-queue "$HOME/.local/share/storyforge/r58/legacy-reuse-queue-v1.jsonl" \
  --private-output "$HOME/.local/share/storyforge/r58/gold192-scope-v1.private.jsonl"
~~~

仅在私人文件中写 195 个匿名 case_id 和 scope_status：192 个 CANDIDATE_ONLY_QUALITY_HOLD，3 个 EXCLUDED_WORLD_ID_UNRESOLVED。该文件不包含故事正文、训练 messages 或 Gold 回复，不得提交 GitHub、外发或视为正式的训练/验证集。SAFE 控制台回执只显示聚合数量。

合成测试：

~~~bash
python3 -m unittest discover -s experiments/r58_quality -p 'test_gold192_scope*.py' -v
ruff check experiments/r58_quality/gold192_scope_exclusion.py experiments/r58_quality/gold192_scope_manifest.py experiments/r58_quality/test_gold192_scope_exclusion.py experiments/r58_quality/test_gold192_scope_manifest.py
~~~
