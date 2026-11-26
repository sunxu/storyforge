# R57 → R58：Dataset v0.4 训练前交接（SAFE）

**文档性质：待 Owner 冻结的推进建议，不是实际训练授权。** 以 Dataset v0.4 准入与训练准备为 R58 主线，新独立评估集建设并行；保持模型晋升与训练准入分开。

## 当前可确认的项目基线

- R46 v0.2 为开发比较基线；R54 v0.3-A 工程训练 PASS、质量 NO-GO。
- R57 B_PROMPT 的旧开发集揭盲结果：B 11、A 5、多数平局 2、无多数 2，探索性 p≈0.2101；仲裁还有 2 HOLD，不晋升。见 `docs/evidence/R57_BPROMPT_DEV20_FINAL_SAFE_20261028.md`。
- 截至 2026-10-27 的交接记录，Dataset v0.4 **正式准入 0 条**；R58 开始时须核对最新状态，不能把此历史值当永久事实。
- R57 数据准入工具与源审计草案位于 **draft PR #5**（`r57/v03b-data-design`）。已有合成测试不等于真实数据准入、来源认证或 Owner 签核。本次归档不顺手合并该 PR。

## R58 准备顺序和闸口

| Gate | 工作 | 通过要求 |
|---|---|---|
| G0 | 明确版本与对照 | 区分 B_PROMPT、B_DATAFIX、B_COMBINED；Owner 预注册训练变量、模型／Prompt SHA、预算 |
| G1 | 数据准入工具核验 | 检查 Schema、拒绝覆盖／符号链接、来源证据、Reviewer 独立性与 fail-closed 测试 |
| G2 | 原始来源与暴露谱系 | Gold195 不自动准入；核对原始 SHA、v0.1/R46/R54 重用、世界别名图和目标时点信息 |
| G3 | 逐项质量审查 | 审核玩家自主权、禁句、硬事实、文学表达、年龄/用途许可；HOLD 隔离，Owner 逐案签核 |
| G4 | Train/Val 冻结 | 按真实语义世界组件隔离并固定输入、目标、split 与哈希；不可按行随机拆分 |
| G5 | 实际 CPU 预检 | 在 HF 环境验证 tokenizer、collator、last_round 标签掩码、上下文长度和运行一致性 |
| G6 | GPU 训练 | 仅 G0–G5 PASS 且 Owner **单独批准指定 HF Job 与费用**后执行 |
| G7 | 独立最终评估 | 新评估题预先封存；旧 R55/R57 开发题不用于正式泛化／晋升结论 |

## 必须保留的风险与边界

- War15 的部分质量/许可边界、Snow14 来源许可、历史三次训练逐输入谱系、世界语义独立性仍需按来源回执核验；Owner 世界声明不等于技术独立认证。
- R50 保护内容不访问、不用于训练、模型选择或新开发题构建。
- GitHub 只允许归档 SAFE 总数与哈希；PRIVATE 故事原文、审阅 CSV、Owner Key、逐题 A/B 映射不得提交。
- 项目训练与计算只用 **Hugging Face**，不用 Mac 或 Docker；不自动提交付费 HF CPU/GPU Job，不覆盖冻结材料，不自动晋升。
- R58 的新评估集可与 v0.4 数据准入并行建立；在正式模型晋升前必须另行冻结并执行。

**状态：** `R57_SAFE_ARCHIVED__R58_DATASET_V04_ADMISSION_PENDING__TRAINING_NOT_AUTHORIZED`。
